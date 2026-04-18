"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CV MODULE 5: ATTENDANCE VERIFICATION PIPELINE (ORCHESTRATOR)              ║
║                                                                              ║
║  Chains all CV modules into a single verify() call:                        ║
║                                                                              ║
║  Input:  raw base64 webcam frame(s) + session context                      ║
║  Output: attendance verdict + full audit trail                              ║
║                                                                              ║
║  Pipeline:                                                                  ║
║    0. Decode & validate image                                               ║
║    1. Filter pipeline (denoise, CLAHE, sharpen)                             ║
║    2. Face detection (InsightFace → MediaPipe → Haar fallback)              ║
║    3. Face quality gate                                                     ║
║    4. Passive liveness (LBP, FFT, gradient, color)                         ║
║    5. Active liveness challenge verification                                ║
║    6. Face recognition (ArcFace + FAISS)                                   ║
║    7. Build annotated debug image                                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import cv2
import numpy as np
import base64
import logging
from dataclasses import dataclass, field
from typing import Optional, List

from app.cv.filters import ImageFilterPipeline, FilterConfig
from app.cv.face_detection import FaceDetector, FaceDetection
from app.cv.liveness import LivenessDetector, LivenessChallenge, PassiveLivenessResult, ActiveLivenessResult
from app.cv.recognition import FaceRecognizer, RecognitionResult
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Full result of the CV attendance verification pipeline."""

    # Final verdict
    verified: bool
    rejection_reason: Optional[str] = None

    # Stage results
    face_detected: bool = False
    face_quality_ok: bool = False
    passive_liveness: Optional[PassiveLivenessResult] = None
    active_liveness: Optional[ActiveLivenessResult] = None
    recognition: Optional[RecognitionResult] = None

    # Matched identity
    matched_student_id: Optional[str] = None

    # Debug / audit
    debug_image_b64: Optional[str] = None        # Annotated image in base64
    filter_stages_b64: Optional[str] = None      # Filter debug grid in base64
    pipeline_log: List[str] = field(default_factory=list)

    @property
    def similarity_score(self) -> float:
        return self.recognition.similarity_score if self.recognition else 0.0

    @property
    def liveness_score(self) -> float:
        return self.passive_liveness.score if self.passive_liveness else 0.0


class AttendanceCVPipeline:
    """
    Singleton CV pipeline that orchestrates all verification stages.
    Instantiated once at startup and reused per request.
    """

    def __init__(self):
        logger.info("[CVPipeline] Initializing CV pipeline...")
        self.filter_pipeline = ImageFilterPipeline(FilterConfig())
        self.face_detector = FaceDetector()
        self.liveness_detector = LivenessDetector()
        self.face_recognizer = FaceRecognizer(
            similarity_threshold=settings.FACE_SIMILARITY_THRESHOLD
        )
        logger.info("[CVPipeline] All CV modules loaded ✓")

    # ─────────────────────────────────────────────────────────────────────────
    # Main verification entry point
    # ─────────────────────────────────────────────────────────────────────────

    def verify(
        self,
        face_image_b64: str,
        liveness_frames_b64: Optional[List[str]] = None,
        liveness_challenge: Optional[str] = None,
        include_debug_image: bool = True,
    ) -> VerificationResult:
        """
        Run full CV verification pipeline.

        Args:
            face_image_b64: Base64-encoded JPEG/PNG from student webcam
            liveness_frames_b64: List of base64 frames for active challenge
            liveness_challenge: Challenge type ('blink'/'nod'/'smile')
            include_debug_image: Whether to generate annotated debug image

        Returns:
            VerificationResult with full audit trail
        """
        result = VerificationResult(verified=False)

        # ── Stage 0: Decode image ─────────────────────────────────────────────
        frame = self._decode_b64_image(face_image_b64)
        if frame is None:
            result.rejection_reason = "Failed to decode image"
            result.pipeline_log.append("❌ Stage 0: Image decode failed")
            return result
        result.pipeline_log.append("✓ Stage 0: Image decoded")

        # ── Stage 1: Filter pipeline ──────────────────────────────────────────
        filter_result = self.filter_pipeline.process(frame, debug=True)
        filtered_frame = filter_result["processed"]
        filter_stages = filter_result["stages"]
        result.pipeline_log.append(
            f"✓ Stage 1: Filters applied: CLAHE, bilateral, unsharp-mask, gamma-correction"
        )

        # ── Stage 2: Face detection ───────────────────────────────────────────
        detections = self.face_detector.detect(filtered_frame)
        if not detections:
            result.rejection_reason = "No face detected in frame"
            result.face_detected = False
            result.pipeline_log.append("❌ Stage 2: No face detected")
            if include_debug_image:
                result.debug_image_b64 = self._encode_debug_image(
                    filtered_frame, detections, "NO FACE DETECTED", (0, 0, 255)
                )
            return result

        result.face_detected = True
        best_face = self.face_detector.get_best_face(detections)
        result.pipeline_log.append(
            f"✓ Stage 2: Face detected (conf={best_face.confidence:.2f}, "
            f"blur={best_face.blur_score:.0f}, quality={best_face.quality_score:.2f})"
        )

        # ── Stage 3: Quality gate ─────────────────────────────────────────────
        if not best_face.is_good_quality:
            result.rejection_reason = (
                f"Face quality too low "
                f"(blur={best_face.blur_score:.0f}, "
                f"yaw={best_face.pose_yaw:.1f}°, "
                f"quality={best_face.quality_score:.2f})"
            )
            result.face_quality_ok = False
            result.pipeline_log.append(f"❌ Stage 3: Quality gate failed — {result.rejection_reason}")
            if include_debug_image:
                result.debug_image_b64 = self._encode_debug_image(
                    self.face_detector.draw_detections(filtered_frame, detections),
                    detections, "LOW QUALITY", (0, 165, 255)
                )
            return result

        result.face_quality_ok = True
        result.pipeline_log.append("✓ Stage 3: Quality gate passed")

        # ── Stage 4: Passive liveness ─────────────────────────────────────────
        face_crop = best_face.face_crop
        passive = self.liveness_detector.passive_liveness(face_crop)
        result.passive_liveness = passive

        if not passive.is_live:
            result.rejection_reason = f"Passive liveness failed: {passive.reason}"
            result.pipeline_log.append(
                f"❌ Stage 4: Passive liveness FAILED "
                f"(score={passive.score:.3f}, "
                f"lbp={passive.lbp_score:.2f}, "
                f"fft={passive.fft_score:.2f}, "
                f"grad={passive.gradient_score:.2f})"
            )
            if include_debug_image:
                result.debug_image_b64 = self._encode_debug_image(
                    self.face_detector.draw_detections(filtered_frame, detections),
                    detections, f"SPOOF DETECTED (score={passive.score:.2f})", (0, 0, 255)
                )
            return result

        result.pipeline_log.append(
            f"✓ Stage 4: Passive liveness passed "
            f"(score={passive.score:.3f}, "
            f"lbp={passive.lbp_score:.2f}, "
            f"fft={passive.fft_score:.2f})"
        )

        # ── Stage 5: Active liveness ──────────────────────────────────────────
        if liveness_frames_b64 and liveness_challenge:
            challenge_frames = [
                f for f in [self._decode_b64_image(b64) for b64 in liveness_frames_b64]
                if f is not None
            ]
            challenge_enum = LivenessChallenge(liveness_challenge)
            active = self.liveness_detector.verify_active_challenge(challenge_frames, challenge_enum)
            result.active_liveness = active

            if not active.passed:
                result.rejection_reason = f"Active liveness challenge failed: {active.reason}"
                result.pipeline_log.append(
                    f"❌ Stage 5: Active challenge ({liveness_challenge}) FAILED — {active.reason}"
                )
                if include_debug_image:
                    result.debug_image_b64 = self._encode_debug_image(
                        self.face_detector.draw_detections(filtered_frame, detections),
                        detections, f"CHALLENGE FAILED: {liveness_challenge.upper()}", (0, 0, 255)
                    )
                return result

            result.pipeline_log.append(
                f"✓ Stage 5: Active challenge ({liveness_challenge}) passed "
                f"(confidence={active.confidence:.2f}, movement={active.detected_movement:.2f})"
            )
        else:
            result.pipeline_log.append("⚠ Stage 5: Active challenge skipped (no frames provided)")

        # ── Stage 6: Face recognition ─────────────────────────────────────────
        recognition = self.face_recognizer.recognize(filtered_frame)
        result.recognition = recognition

        if not recognition.matched:
            result.rejection_reason = (
                f"Face not recognized "
                f"(best similarity={recognition.similarity_score:.3f}, "
                f"threshold={recognition.threshold_used:.3f})"
            )
            result.pipeline_log.append(
                f"❌ Stage 6: Recognition FAILED "
                f"(similarity={recognition.similarity_score:.3f} < threshold={recognition.threshold_used:.3f})"
            )
            if include_debug_image:
                result.debug_image_b64 = self._encode_debug_image(
                    self.face_detector.draw_detections(filtered_frame, detections),
                    detections, f"NOT RECOGNIZED ({recognition.similarity_score:.3f})", (0, 0, 255)
                )
            return result

        result.matched_student_id = recognition.student_id
        result.pipeline_log.append(
            f"✓ Stage 6: Recognition passed — matched {recognition.student_id} "
            f"(similarity={recognition.similarity_score:.3f})"
        )

        # ── All stages passed ─────────────────────────────────────────────────
        result.verified = True
        result.pipeline_log.append("✅ ATTENDANCE VERIFIED")

        if include_debug_image:
            annotated = self.face_detector.draw_detections(filtered_frame, detections)
            annotated = self._draw_verification_overlay(
                annotated, result, best_face
            )
            result.debug_image_b64 = self._encode_image_b64(annotated)

        # Attach filter debug grid
        if filter_stages:
            grid = self.filter_pipeline.draw_filter_debug_overlay(filter_stages)
            result.filter_stages_b64 = self._encode_image_b64(grid)

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Enrollment proxy
    # ─────────────────────────────────────────────────────────────────────────

    def enroll(self, student_id: str, face_image_b64: str) -> tuple[bool, str]:
        """Decode image and enroll student face."""
        frame = self._decode_b64_image(face_image_b64)
        if frame is None:
            return False, "Could not decode enrollment image"
        return self.face_recognizer.enroll_student(student_id, frame)

    def get_challenge(self) -> str:
        """Get a random liveness challenge type."""
        return self.liveness_detector.get_random_challenge().value

    # ─────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _decode_b64_image(self, b64_string: str) -> Optional[np.ndarray]:
        """Decode base64 image string to numpy BGR array."""
        try:
            # Strip data URL prefix if present
            if "," in b64_string:
                b64_string = b64_string.split(",", 1)[1]
            data = base64.b64decode(b64_string)
            nparr = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            logger.error(f"Image decode error: {e}")
            return None

    def _encode_image_b64(self, image: np.ndarray) -> str:
        """Encode numpy BGR array to base64 JPEG string."""
        _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(buffer).decode("utf-8")

    def _encode_debug_image(
        self,
        frame: np.ndarray,
        detections,
        label: str,
        color: tuple,
    ) -> str:
        """Create annotated debug image and encode as base64."""
        vis = frame.copy()
        h, w = vis.shape[:2]
        # Semi-transparent banner
        overlay = vis.copy()
        cv2.rectangle(overlay, (0, h - 40), (w, h), color, -1)
        cv2.addWeighted(overlay, 0.6, vis, 0.4, 0, vis)
        cv2.putText(vis, label, (10, h - 12),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        return self._encode_image_b64(vis)

    def _draw_verification_overlay(
        self,
        frame: np.ndarray,
        result: VerificationResult,
        face: FaceDetection,
    ) -> np.ndarray:
        """Draw full verification info overlay on frame."""
        h, w = frame.shape[:2]
        overlay = frame.copy()

        # Green success banner
        cv2.rectangle(overlay, (0, h - 80), (w, h), (0, 180, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Student ID + scores
        cv2.putText(frame, f"VERIFIED: {result.matched_student_id}",
                   (10, h - 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame,
                   f"Sim:{result.similarity_score:.2f}  Live:{result.liveness_score:.2f}  Blur:{face.blur_score:.0f}",
                   (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 255, 200), 1)

        return frame


# ── Module-level singleton (import this in API routes) ─────────────────────

_pipeline_instance: Optional[AttendanceCVPipeline] = None


def get_cv_pipeline() -> AttendanceCVPipeline:
    """FastAPI dependency — returns the singleton CV pipeline."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = AttendanceCVPipeline()
    return _pipeline_instance
