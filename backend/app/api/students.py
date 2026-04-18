"""Student management API routes (enrollment / onboarding)."""

import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import get_current_user, require_teacher
from app.models.user import User, UserRole
from app.models.otp import OTPRecord
from app.schemas.schemas import StudentOut, EnrollFaceRequest
from app.cv.pipeline import get_cv_pipeline, AttendanceCVPipeline

router = APIRouter()


@router.get("/", response_model=List[StudentOut])
def list_students(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all students. Accessible by teacher or the student themselves."""
    if current_user.role == UserRole.TEACHER:
        students = db.exec(select(User).where(User.role == UserRole.STUDENT)).all()
    else:
        students = [current_user]
    return students


@router.post("/enroll-face")
def enroll_face(
    req: EnrollFaceRequest,
    db: Session = Depends(get_session),
    cv_pipeline: AttendanceCVPipeline = Depends(get_cv_pipeline),
):
    """
    Onboard + enroll a student's face. NO JWT required — the OTP
    verification_token is the sole proof of identity.

    Flow:
      1. Student entered their @muj email and verified via OTP → got a token
      2. This endpoint uses the token to find the verified email
      3. If no account exists for that email, one is CREATED (onboarding)
      4. CV pipeline validates face quality and stores embedding
      5. Student is now enrolled and can mark attendance

    One enrollment per email. Token is single-use.
    """
    # ── 1. Resolve the verification token to an email ────────────────────────
    otp_record = db.exec(
        select(OTPRecord)
        .where(OTPRecord.verified == True)  # noqa: E712
        .where(OTPRecord.verification_token == req.verification_token)
        .where(OTPRecord.created_at > datetime.utcnow() - timedelta(minutes=10))
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=403,
            detail="Invalid or expired verification token. Please verify your email again.",
        )

    enrollment_email = otp_record.email

    # ── 2. Find or CREATE the student account ────────────────────────────────
    student = db.exec(
        select(User).where(User.email == enrollment_email)
    ).first()

    if student and student.face_enrolled:
        raise HTTPException(
            status_code=409,
            detail=f"Face already enrolled for {enrollment_email}. Contact your teacher to reset.",
        )

    if not student:
        # Onboarding: create the student account
        student = User(
            id=f"student-{uuid.uuid4().hex[:8]}",
            name=req.student_name.strip(),
            email=enrollment_email,
            password_plain="",  # No password — face-only auth after enrollment
            role=UserRole.STUDENT,
        )
        db.add(student)
        db.commit()
        db.refresh(student)
        print(f"[ONBOARD] Created new student: {student.name} ({enrollment_email})")

    # If account existed but name was a placeholder, update it
    if student.name != req.student_name.strip() and req.student_name.strip():
        student.name = req.student_name.strip()
        db.add(student)
        db.commit()

    # ── 3. Consume the token (single-use) ────────────────────────────────────
    otp_record.verification_token = None
    db.add(otp_record)
    db.commit()

    # ── 4. CV pipeline enrollment ────────────────────────────────────────────
    success, message = cv_pipeline.enroll(student.id, req.face_image_b64)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    # ── 5. Mark enrolled ─────────────────────────────────────────────────────
    student.face_enrolled = True
    db.add(student)
    db.commit()

    return {
        "success": True,
        "message": message,
        "enrolled_email": enrollment_email,
        "enrolled_name": student.name,
    }


@router.delete("/{student_id}/enrollment")
def remove_enrollment(
    student_id: str,
    db: Session = Depends(get_session),
    teacher: User = Depends(require_teacher),
    cv_pipeline: AttendanceCVPipeline = Depends(get_cv_pipeline),
):
    """Remove a student's face enrollment. Teacher only."""
    student = db.get(User, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    cv_pipeline.face_recognizer.remove_enrollment(student_id)
    student.face_enrolled = False
    db.add(student)
    db.commit()

    return {"success": True, "message": f"Enrollment removed for {student.name}"}
