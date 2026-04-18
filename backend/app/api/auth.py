"""Auth API routes — login + OTP email verification for onboarding."""

import random
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import create_access_token
from app.core.config import settings
from app.core.email import send_otp_email
from app.models.user import User, UserRole
from app.models.otp import OTPRecord
from app.schemas.schemas import (
    LoginRequest, TokenResponse, SendOTPRequest, VerifyOTPRequest, VerifyOTPResponse,
)

router = APIRouter()

ALLOWED_EMAIL_DOMAIN = "@muj.manipal.edu"


def _validate_email_domain(email: str):
    """Reject any email that is not from the allowed institutional domain."""
    if not email.lower().endswith(ALLOWED_EMAIL_DOMAIN):
        raise HTTPException(
            status_code=400,
            detail=f"Only {ALLOWED_EMAIL_DOMAIN} email addresses are allowed",
        )


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_session)):
    """Authenticate with institutional email only."""
    _validate_email_domain(req.email)

    user = db.exec(select(User).where(User.email == req.email.lower().strip())).first()

    if not user or user.password_plain != req.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.id, "role": user.role.value})

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        roll_number=user.roll_number,
        face_enrolled=user.face_enrolled,
    )


# ─── OTP Endpoints (public — no JWT required, this IS onboarding) ───────────

@router.post("/send-otp")
def send_otp(
    req: SendOTPRequest,
    db: Session = Depends(get_session),
):
    """
    Send a 6-digit OTP to any @muj.manipal.edu email.
    This is the first step of student onboarding — no account needed yet.
    The OTP proves the student owns this email address.

    If the email already has a face enrolled, reject (one enrollment per email).
    """
    email = req.email.lower().strip()
    _validate_email_domain(email)

    # Check if this email already has a face enrolled
    existing_user = db.exec(select(User).where(User.email == email)).first()
    if existing_user and existing_user.face_enrolled:
        raise HTTPException(
            status_code=409,
            detail=f"Face already enrolled for {email}. Contact your teacher to reset.",
        )

    # Rate limit: max 1 OTP per 60 seconds per email
    recent = db.exec(
        select(OTPRecord)
        .where(OTPRecord.email == email)
        .where(OTPRecord.created_at > datetime.utcnow() - timedelta(seconds=60))
    ).first()
    if recent:
        raise HTTPException(status_code=429, detail="OTP already sent. Wait 60 seconds.")

    # Generate 6-digit OTP
    otp_code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    otp_record = OTPRecord(
        email=email,
        otp_code=otp_code,
        expires_at=expires_at,
    )
    db.add(otp_record)
    db.commit()

    # Send the OTP via real email (if SMTP configured) or console fallback
    email_sent = send_otp_email(email, otp_code)

    # Always log to console for backend visibility
    print(f"\n{'='*50}")
    print(f"  OTP for {email}: {otp_code}")
    print(f"  Email sent: {email_sent}")
    print(f"  Expires at: {expires_at.isoformat()}")
    print(f"{'='*50}\n")

    response: dict = {
        "message": f"OTP sent to {email}",
        "email_delivered": email_sent,
        "expires_in_seconds": 300,
    }
    # In DEBUG mode with no SMTP, also return OTP in response for testing
    if settings.DEBUG and not email_sent:
        response["dev_otp"] = otp_code

    return response


@router.post("/verify-otp", response_model=VerifyOTPResponse)
def verify_otp(
    req: VerifyOTPRequest,
    db: Session = Depends(get_session),
):
    """
    Verify the OTP for any @muj.manipal.edu email.
    No account needed — this is onboarding.
    Returns a one-time verification_token required for face enrollment.
    """
    email = req.email.lower().strip()
    _validate_email_domain(email)

    # Find the latest non-verified OTP for this email
    otp_record = db.exec(
        select(OTPRecord)
        .where(OTPRecord.email == email)
        .where(OTPRecord.verified == False)  # noqa: E712
        .where(OTPRecord.expires_at > datetime.utcnow())
        .order_by(OTPRecord.created_at.desc())  # type: ignore
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="No valid OTP found. Request a new one.")

    if otp_record.otp_code != req.otp_code:
        raise HTTPException(status_code=400, detail="Incorrect OTP")

    # Mark as verified and generate a one-time token for enrollment
    verification_token = str(uuid.uuid4())
    otp_record.verified = True
    otp_record.verification_token = verification_token
    db.add(otp_record)
    db.commit()

    return VerifyOTPResponse(
        verified=True,
        verification_token=verification_token,
        email=email,
        message="Email verified! Enter your name and enroll your face.",
    )
