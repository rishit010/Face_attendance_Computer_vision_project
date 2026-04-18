"""Session management API routes (Teacher only)."""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import get_current_user, require_teacher
from app.models.session import AttendanceSession, SessionStatus, AttendanceRecord
from app.models.user import User
from app.schemas.schemas import CreateSessionRequest, SessionResponse, AttendanceRecordOut

router = APIRouter()


@router.post("/create", response_model=SessionResponse)
def create_session(
    req: CreateSessionRequest,
    db: Session = Depends(get_session),
    teacher: User = Depends(require_teacher),
):
    """Create a new attendance session. Teacher only."""
    session_id = str(uuid.uuid4())[:8].upper()

    expires_at = None
    if req.duration_minutes:
        expires_at = datetime.utcnow() + timedelta(minutes=req.duration_minutes)

    att_session = AttendanceSession(
        id=session_id,
        teacher_id=teacher.id,
        course_name=req.course_name,
        classroom_lat=req.classroom_lat,
        classroom_lon=req.classroom_lon,
        classroom_gps_accuracy=req.classroom_gps_accuracy,
        room_radius_meters=req.room_radius_meters,
        expires_at=expires_at,
    )
    db.add(att_session)
    db.commit()
    db.refresh(att_session)
    return att_session


@router.get("/active", response_model=List[SessionResponse])
def get_active_sessions(db: Session = Depends(get_session)):
    """Get all currently active sessions (visible to students to join)."""
    now = datetime.utcnow()
    sessions = db.exec(
        select(AttendanceSession).where(
            AttendanceSession.status == SessionStatus.ACTIVE
        )
    ).all()

    # Auto-expire sessions past their duration
    active = []
    for s in sessions:
        if s.expires_at and s.expires_at < now:
            s.status = SessionStatus.CLOSED
            s.closed_at = now
            db.add(s)
            db.commit()
        else:
            active.append(s)

    return active


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_by_id(session_id: str, db: Session = Depends(get_session)):
    s = db.get(AttendanceSession, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


@router.post("/{session_id}/close")
def close_session(
    session_id: str,
    db: Session = Depends(get_session),
    teacher: User = Depends(require_teacher),
):
    s = db.get(AttendanceSession, session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    if s.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="Not your session")

    s.status = SessionStatus.CLOSED
    s.closed_at = datetime.utcnow()
    db.add(s)
    db.commit()
    return {"message": "Session closed"}


@router.get("/{session_id}/attendance", response_model=List[AttendanceRecordOut])
def get_session_attendance(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Get all attendance records for a session."""
    records = db.exec(
        select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
    ).all()

    result = []
    for rec in records:
        student = db.get(User, rec.student_id)
        result.append(
            AttendanceRecordOut(
                id=rec.id,
                student_id=rec.student_id,
                student_name=student.name if student else "Unknown",
                student_email=student.email if student else "unknown",
                roll_number=student.roll_number if student else None,
                status=rec.status,
                face_similarity_score=rec.face_similarity_score,
                liveness_score=rec.liveness_score,
                distance_from_class_meters=rec.distance_from_class_meters,
                marked_at=rec.marked_at,
            )
        )
    return result
