"""
Session and Attendance database models.
"""

from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class SessionStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    REJECTED_LOCATION = "rejected_location"
    REJECTED_FACE = "rejected_face"
    REJECTED_LIVENESS = "rejected_liveness"
    REJECTED_NO_FACE = "rejected_no_face"


class AttendanceSession(SQLModel, table=True):
    __tablename__ = "attendance_sessions"

    id: str = Field(primary_key=True)
    teacher_id: str = Field(foreign_key="users.id")
    course_name: str
    status: SessionStatus = SessionStatus.ACTIVE

    # Classroom geofence
    classroom_lat: float
    classroom_lon: float
    room_radius_meters: float = 20.0
    classroom_gps_accuracy: Optional[float] = None  # Browser-reported accuracy in metres

    # Time window
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class AttendanceRecord(SQLModel, table=True):
    __tablename__ = "attendance_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="attendance_sessions.id")
    student_id: str = Field(foreign_key="users.id")
    status: AttendanceStatus

    # CV verification details (for audit/debugging)
    face_similarity_score: Optional[float] = None
    liveness_score: Optional[float] = None
    liveness_challenge_passed: Optional[bool] = None

    # Location details
    student_lat: Optional[float] = None
    student_lon: Optional[float] = None
    distance_from_class_meters: Optional[float] = None

    # Which filters were applied (stored as JSON string)
    cv_filters_applied: Optional[str] = None

    marked_at: datetime = Field(default_factory=datetime.utcnow)
