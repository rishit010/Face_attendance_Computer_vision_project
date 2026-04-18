"""
Attendance marking API route — the core CV verification endpoint.
This is where the full pipeline is invoked.
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.core.security import require_student
from app.core.geofence import GeoPoint, is_within_radius, validate_location_data
from app.models.session import AttendanceSession, SessionStatus, AttendanceRecord, AttendanceStatus
from app.models.user import User
from app.schemas.schemas import MarkAttendanceRequest, AttendanceResult
from app.cv.pipeline import get_cv_pipeline, AttendanceCVPipeline

router = APIRouter()


@router.post("/mark", response_model=AttendanceResult)
def mark_attendance(
    req: MarkAttendanceRequest,
    db: Session = Depends(get_session),
    student: User = Depends(require_student),
    cv_pipeline: AttendanceCVPipeline = Depends(get_cv_pipeline),
):
    """
    Full attendance marking endpoint.

    Checks (in order — early rejection at each stage):
      1. Session exists and is active
      2. GPS coordinates are valid
      3. Student is within classroom geofence
      4. CV pipeline: filters → face detection → quality → liveness → recognition
      5. Resolve real student identity from face recognition result
      6. Duplicate check (per real student, not portal user)
      7. Mark present
    """

    # ── 1. Session validation ─────────────────────────────────────────────────
    session = db.get(AttendanceSession, req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    if session.expires_at and session.expires_at < datetime.utcnow():
        session.status = SessionStatus.CLOSED
        db.add(session)
        db.commit()
        raise HTTPException(status_code=400, detail="Session has expired")

    # ── 2. Location validation ────────────────────────────────────────────────
    if not validate_location_data(req.student_lat, req.student_lon):
        _save_rejection(db, req, student.id, AttendanceStatus.REJECTED_LOCATION,
                        req.student_lat, req.student_lon, None)
        return AttendanceResult(
            success=False,
            status=AttendanceStatus.REJECTED_LOCATION,
            message="Invalid GPS coordinates reported",
        )

    # ── 3. Geofence check ─────────────────────────────────────────────────────
    student_loc = GeoPoint(req.student_lat, req.student_lon)
    classroom_loc = GeoPoint(session.classroom_lat, session.classroom_lon)

    # Dynamic GPS error buffer: sum of teacher's and student's reported accuracy
    # Browser GPS accuracy can be 50-300m on laptops (WiFi positioning)
    teacher_accuracy = session.classroom_gps_accuracy or 0
    student_accuracy = req.student_gps_accuracy or 0
    gps_buffer = max(teacher_accuracy + student_accuracy, 50.0)  # minimum 50m

    is_inside, distance = is_within_radius(student_loc, classroom_loc, session.room_radius_meters, gps_buffer)

    if not is_inside:
        _save_rejection(db, req, student.id, AttendanceStatus.REJECTED_LOCATION,
                        req.student_lat, req.student_lon, distance)
        return AttendanceResult(
            success=False,
            status=AttendanceStatus.REJECTED_LOCATION,
            message=f"You are {distance:.0f}m from the classroom (max {session.room_radius_meters:.0f}m)",
            distance_meters=distance,
        )

    # ── 5. CV Pipeline ────────────────────────────────────────────────────────
    cv_result = cv_pipeline.verify(
        face_image_b64=req.face_image_b64,
        liveness_frames_b64=req.liveness_frames_b64,
        liveness_challenge=req.liveness_challenge_type,
        include_debug_image=True,
    )

    if not cv_result.verified:
        # Map CV rejection to attendance status
        if not cv_result.face_detected:
            att_status = AttendanceStatus.REJECTED_NO_FACE
        elif cv_result.passive_liveness and not cv_result.passive_liveness.is_live:
            att_status = AttendanceStatus.REJECTED_LIVENESS
        elif cv_result.active_liveness and not cv_result.active_liveness.passed:
            att_status = AttendanceStatus.REJECTED_LIVENESS
        else:
            att_status = AttendanceStatus.REJECTED_FACE

        _save_rejection(db, req, student.id, att_status,
                        req.student_lat, req.student_lon, distance,
                        face_sim=cv_result.similarity_score,
                        liveness=cv_result.liveness_score,
                        pipeline_log=cv_result.pipeline_log)

        return AttendanceResult(
            success=False,
            status=att_status,
            message=cv_result.rejection_reason or "Verification failed",
            face_similarity_score=cv_result.similarity_score,
            liveness_score=cv_result.liveness_score,
            debug_image_b64=cv_result.debug_image_b64,
        )

    # ── 6. Resolve real student identity from face recognition ────────────────
    # With the shared portal model, the JWT user is "student-portal" but
    # face recognition identifies the actual enrolled student.
    real_student_id = cv_result.matched_student_id or student.id
    real_student = db.get(User, real_student_id)

    if not real_student:
        return AttendanceResult(
            success=False,
            status=AttendanceStatus.REJECTED_FACE,
            message="Face not enrolled. Please enroll first.",
            face_similarity_score=cv_result.similarity_score,
            debug_image_b64=cv_result.debug_image_b64,
        )

    # ── 7. Duplicate check (using real student, not portal user) ──────────────
    existing = db.exec(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == req.session_id,
            AttendanceRecord.student_id == real_student.id,
            AttendanceRecord.status == AttendanceStatus.PRESENT,
        )
    ).first()

    if existing:
        return AttendanceResult(
            success=False,
            status=AttendanceStatus.PRESENT,
            message=f"Attendance already marked for {real_student.email}",
        )

    # ── 8. Mark present ───────────────────────────────────────────────────────
    record = AttendanceRecord(
        session_id=req.session_id,
        student_id=real_student.id,
        status=AttendanceStatus.PRESENT,
        face_similarity_score=cv_result.similarity_score,
        liveness_score=cv_result.liveness_score,
        liveness_challenge_passed=True if cv_result.active_liveness else None,
        student_lat=req.student_lat,
        student_lon=req.student_lon,
        distance_from_class_meters=distance,
        cv_filters_applied=json.dumps(["clahe", "bilateral", "unsharp_mask", "gamma"]),
    )
    db.add(record)
    db.commit()

    return AttendanceResult(
        success=True,
        status=AttendanceStatus.PRESENT,
        message=f"Attendance marked! Welcome, {real_student.name}",
        face_similarity_score=cv_result.similarity_score,
        liveness_score=cv_result.liveness_score,
        liveness_challenge_passed=True,
        distance_meters=distance,
        debug_image_b64=cv_result.debug_image_b64,
    )


@router.get("/challenge")
def get_liveness_challenge(cv_pipeline: AttendanceCVPipeline = Depends(get_cv_pipeline)):
    """Get a random liveness challenge type for the student to perform."""
    return {"challenge": cv_pipeline.get_challenge()}


def _save_rejection(
    db, req, student_id, status, lat, lon, distance,
    face_sim=None, liveness=None, pipeline_log=None
):
    record = AttendanceRecord(
        session_id=req.session_id,
        student_id=student_id,
        status=status,
        face_similarity_score=face_sim,
        liveness_score=liveness,
        student_lat=lat,
        student_lon=lon,
        distance_from_class_meters=distance,
        cv_filters_applied=json.dumps(pipeline_log or []),
    )
    db.add(record)
    db.commit()
