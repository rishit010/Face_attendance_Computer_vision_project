"""
OTP model for email verification before face enrollment.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class OTPRecord(SQLModel, table=True):
    __tablename__ = "otp_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    otp_code: str
    verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    # Once verified, issue a one-time token the student sends with enroll-face
    verification_token: Optional[str] = None
