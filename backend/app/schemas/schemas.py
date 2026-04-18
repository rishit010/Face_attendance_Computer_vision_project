"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.user import UserRole
from app.models.session import SessionStatus, AttendanceStatus


# ─── Auth ────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    name: str
    email: str
    role: UserRole
    roll_number: Optional[str] = None
    face_enrolled: bool = False


# ─── OTP ─────────────────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp_code: str

class VerifyOTPResponse(BaseModel):
    verified: bool
    verification_token: str
    email: str
    message: str


# ─── Session ─────────────────────────────────────────────────────────────────

class CreateSessionRequest(BaseModel):
    course_name: str
    classroom_lat: float
    classroom_lon: float
    classroom_gps_accuracy: Optional[float] = None
    room_radius_meters: float = 20.0
    duration_minutes: Optional[int] = 30

class SessionResponse(BaseModel):
    id: str
    teacher_id: str
    course_name: str
    status: SessionStatus
    classroom_lat: float
    classroom_lon: float
    classroom_gps_accuracy: Optional[float] = None
    room_radius_meters: float
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Attendance ───────────────────────────────────────────────────────────────

class MarkAttendanceRequest(BaseModel):
    session_id: str
    student_lat: float
    student_lon: float
    student_gps_accuracy: Optional[float] = None  # Browser-reported accuracy in metres
    # Base64-encoded JPEG/PNG image from webcam
    face_image_b64: str
    # Active liveness challenge frames (list of base64 images)
    liveness_frames_b64: Optional[List[str]] = None
    # Which challenge was issued (blink / nod / smile)
    liveness_challenge_type: Optional[str] = None

class AttendanceResult(BaseModel):
    success: bool
    status: AttendanceStatus
    message: str
    # CV debug info
    face_similarity_score: Optional[float] = None
    liveness_score: Optional[float] = None
    liveness_challenge_passed: Optional[bool] = None
    distance_meters: Optional[float] = None
    # Processed image with annotations (base64) for debug view
    debug_image_b64: Optional[str] = None

class AttendanceRecordOut(BaseModel):
    id: int
    student_id: str
    student_name: str
    student_email: str
    roll_number: Optional[str]
    status: AttendanceStatus
    face_similarity_score: Optional[float]
    liveness_score: Optional[float]
    distance_from_class_meters: Optional[float]
    marked_at: datetime

    class Config:
        from_attributes = True


# ─── Students ─────────────────────────────────────────────────────────────────

class StudentOut(BaseModel):
    id: str
    name: str
    email: str
    roll_number: Optional[str]
    face_enrolled: bool

    class Config:
        from_attributes = True

class EnrollFaceRequest(BaseModel):
    # Base64-encoded image for enrollment
    face_image_b64: str
    # One-time token from OTP verification — required
    verification_token: str
    # Student's full name (for account creation during onboarding)
    student_name: str
