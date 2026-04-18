"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CV MODULE 2: FACE DETECTION                                                ║
║                                                                              ║
║  Multi-model detection pipeline:                                             ║
║  1. Primary: InsightFace RetinaFace (SOTA accuracy, landmark detection)     ║
║  2. Fallback: OpenCV Haar Cascade (lightweight, runs without GPU)           ║
║  3. Fallback 2: MediaPipe Face Detection (fast, mobile-optimised)           ║
║                                                                              ║
║  Also computes:                                                              ║
║  - Face quality score (blur, brightness, pose angle)                        ║
║  - 5-point landmark alignment for canonical face crop                       ║
║  - Bounding box padding and face crop extraction                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging
import os

logger = logging.getLogger(__name__)


@dataclass
class FaceDetection:
    """Represents a single detected face and all associated data."""
    bbox: Tuple[int, int, int, int]        # (x1, y1, x2, y2)
    confidence: float                       # Detection confidence 0–1
    landmarks: Optional[np.ndarray]         # 5 facial landmarks (eyes, nose, mouth corners)
    face_crop: Optional[np.ndarray]         # Aligned face crop (BGR)
    quality_score: float = 0.0             # Face quality 0–1 (higher = better)
    pose_yaw: float = 0.0                  # Head pose: yaw (left/right) degrees
    pose_pitch: float = 0.0               # Head pose: pitch (up/down) degrees
    blur_score: float = 0.0               # Laplacian variance (higher = sharper)

    @property
    def area(self) -> int:
        x1, y1, x2, y2 = self.bbox
        return (x2 - x1) * (y2 - y1)

    @property
    def is_good_quality(self) -> bool:
        """Minimum quality gate before running recognition."""
        return (
            self.quality_score >= 0.4
            and self.blur_score >= 80.0
            and abs(self.pose_yaw) <= 35
            and abs(self.pose_pitch) <= 30
        )


class FaceDetector:
    """
    Multi-model face detector with automatic fallback.

    Usage:
        detector = FaceDetector()
        detections = detector.detect(frame)
        best_face = detector.get_best_face(detections)
    """

    def __init__(self, prefer_insightface: bool = True):
        self.insightface_model = None
        self.haar_cascade = None
        self.mediapipe_detector = None
        self.prefer_insightface = prefer_insightface
        self._init_detectors()

    def _init_detectors(self):
        """Initialize available detectors, gracefully falling back."""

        # Primary: InsightFace RetinaFace
        if self.prefer_insightface:
            try:
                import insightface
                from insightface.app import FaceAnalysis
                self.insightface_model = FaceAnalysis(
                    name="buffalo_l",
                    providers=["CPUExecutionProvider"],
                )
                self.insightface_model.prepare(ctx_id=0, det_size=(640, 640))
                logger.info("[FaceDetector] InsightFace (RetinaFace) loaded ✓")
            except Exception as e:
                logger.warning(f"[FaceDetector] InsightFace not available: {e}")

        # Fallback: Haar Cascade (always available with OpenCV)
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        if os.path.exists(cascade_path):
            self.haar_cascade = cv2.CascadeClassifier(cascade_path)
            logger.info("[FaceDetector] Haar Cascade loaded ✓")

        # Fallback 2: MediaPipe
        try:
            import mediapipe as mp
            mp_face = mp.solutions.face_detection
            self.mediapipe_detector = mp_face.FaceDetection(
                model_selection=1,          # 1 = full range model
                min_detection_confidence=0.5,
            )
            logger.info("[FaceDetector] MediaPipe Face Detection loaded ✓")
        except Exception as e:
            logger.warning(f"[FaceDetector] MediaPipe not available: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray) -> List[FaceDetection]:
        """
        Detect all faces in a frame.
        Tries detectors in order: InsightFace → MediaPipe → Haar.

        Returns list of FaceDetection objects sorted by confidence desc.
        """
        detections = []

        if self.insightface_model is not None:
            detections = self._detect_insightface(frame)
        elif self.mediapipe_detector is not None:
            detections = self._detect_mediapipe(frame)
        elif self.haar_cascade is not None:
            detections = self._detect_haar(frame)

        # Sort by area (largest = closest face = most likely the student)
        detections.sort(key=lambda d: d.area, reverse=True)
        return detections

    def get_best_face(self, detections: List[FaceDetection]) -> Optional[FaceDetection]:
        """
        Return the best face for recognition:
        - Must pass quality gate
        - Largest face (closest to camera)
        """
        for det in detections:
            if det.is_good_quality:
                return det
        # Return largest even if quality is low (let recognition layer decide)
        return detections[0] if detections else None

    # ─────────────────────────────────────────────────────────────────────────
    # Detection backends
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_insightface(self, frame: np.ndarray) -> List[FaceDetection]:
        """Use InsightFace RetinaFace — most accurate, gives 5-pt landmarks."""
        try:
            faces = self.insightface_model.get(frame)
        except Exception as e:
            logger.error(f"InsightFace detection error: {e}")
            return []

        results = []
        for face in faces:
            x1, y1, x2, y2 = map(int, face.bbox)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)

            landmarks = face.kps.astype(np.int32) if face.kps is not None else None
            crop = self._align_face(frame, landmarks, face.bbox) if landmarks is not None else frame[y1:y2, x1:x2]

            det = FaceDetection(
                bbox=(x1, y1, x2, y2),
                confidence=float(face.det_score),
                landmarks=landmarks,
                face_crop=crop,
            )
            self._compute_quality(frame, det)
            results.append(det)

        return results

    def _detect_mediapipe(self, frame: np.ndarray) -> List[FaceDetection]:
        """Use MediaPipe — good fallback, gives 6 key points."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.mediapipe_detector.process(rgb)

        if not result.detections:
            return []

        h, w = frame.shape[:2]
        detections = []
        for detection in result.detections:
            bb = detection.location_data.relative_bounding_box
            x1 = int(bb.xmin * w)
            y1 = int(bb.ymin * h)
            x2 = int((bb.xmin + bb.width) * w)
            y2 = int((bb.ymin + bb.height) * h)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            crop = frame[y1:y2, x1:x2] if (x2 > x1 and y2 > y1) else None
            det = FaceDetection(
                bbox=(x1, y1, x2, y2),
                confidence=detection.score[0],
                landmarks=None,
                face_crop=crop,
            )
            self._compute_quality(frame, det)
            detections.append(det)

        return detections

    def _detect_haar(self, frame: np.ndarray) -> List[FaceDetection]:
        """Haar cascade fallback — classic CV approach, fast but less accurate."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)  # Improve contrast for Haar

        faces_rect = self.haar_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        if len(faces_rect) == 0:
            return []

        detections = []
        for (x, y, w, h) in faces_rect:
            x2, y2 = x + w, y + h
            crop = frame[y:y2, x:x2]
            det = FaceDetection(
                bbox=(x, y, x2, y2),
                confidence=0.75,   # Haar doesn't give confidence — use fixed value
                landmarks=None,
                face_crop=crop,
            )
            self._compute_quality(frame, det)
            detections.append(det)

        return detections

    # ─────────────────────────────────────────────────────────────────────────
    # Face alignment (5-point landmarks → canonical crop)
    # ─────────────────────────────────────────────────────────────────────────

    def _align_face(
        self,
        frame: np.ndarray,
        landmarks: np.ndarray,
        bbox: np.ndarray,
        target_size: int = 112,
    ) -> np.ndarray:
        """
        Align face to canonical position using similarity transform.

        The 5 landmark points (left eye, right eye, nose tip,
        left mouth corner, right mouth corner) are mapped to fixed
        reference positions — this makes the face embedding
        rotation and scale invariant.
        """
        # ArcFace reference landmarks (112x112 target)
        reference_landmarks = np.array([
            [38.2946, 51.6963],   # left eye
            [73.5318, 51.5014],   # right eye
            [56.0252, 71.7366],   # nose tip
            [41.5493, 92.3655],   # left mouth corner
            [70.7299, 92.2041],   # right mouth corner
        ], dtype=np.float32)

        src = landmarks[:5].astype(np.float32)
        M, _ = cv2.estimateAffinePartial2D(src, reference_landmarks)

        if M is None:
            # Fallback to simple crop
            x1, y1, x2, y2 = map(int, bbox)
            crop = frame[max(0,y1):y2, max(0,x1):x2]
            return cv2.resize(crop, (target_size, target_size)) if crop.size > 0 else np.zeros((target_size, target_size, 3), dtype=np.uint8)

        aligned = cv2.warpAffine(frame, M, (target_size, target_size))
        return aligned

    # ─────────────────────────────────────────────────────────────────────────
    # Face quality assessment
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_quality(self, frame: np.ndarray, detection: FaceDetection):
        """
        Compute multiple face quality metrics:
        1. Blur score (Laplacian variance)
        2. Brightness check
        3. Approximate head pose from landmark geometry
        4. Overall quality score
        """
        x1, y1, x2, y2 = detection.bbox
        face_region = frame[y1:y2, x1:x2]

        if face_region.size == 0:
            return

        # ── Blur score: Laplacian variance ───────────────────────────────────
        # High variance = sharp image; low variance = blurry
        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        detection.blur_score = float(cv2.Laplacian(gray_face, cv2.CV_64F).var())

        # ── Brightness check ─────────────────────────────────────────────────
        hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)
        brightness = float(np.mean(hsv[:, :, 2]))
        brightness_ok = 40 < brightness < 220

        # ── Head pose from landmark geometry ─────────────────────────────────
        if detection.landmarks is not None and len(detection.landmarks) >= 5:
            lm = detection.landmarks
            left_eye, right_eye = lm[0], lm[1]
            eye_dx = right_eye[0] - left_eye[0]
            eye_dy = right_eye[1] - left_eye[1]
            # Yaw approximation from horizontal eye distance asymmetry
            face_w = x2 - x1
            eye_span = abs(eye_dx)
            detection.pose_yaw = (1 - eye_span / (face_w * 0.6 + 1e-6)) * 45
            # Pitch approximation from vertical eye displacement
            detection.pose_pitch = float(np.degrees(np.arctan2(abs(eye_dy), abs(eye_dx) + 1e-6)))

        # ── Overall quality score (0–1) ───────────────────────────────────────
        blur_norm = min(detection.blur_score / 500.0, 1.0)
        brightness_score = 1.0 if brightness_ok else 0.3
        pose_score = max(0, 1 - abs(detection.pose_yaw) / 45.0)

        detection.quality_score = (
            0.5 * blur_norm +
            0.2 * brightness_score +
            0.3 * pose_score
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Visualization
    # ─────────────────────────────────────────────────────────────────────────

    def draw_detections(
        self, frame: np.ndarray, detections: List[FaceDetection]
    ) -> np.ndarray:
        """Draw bounding boxes, landmarks, and quality info on frame."""
        vis = frame.copy()

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = (0, 255, 0) if det.is_good_quality else (0, 165, 255)

            # Bounding box
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)

            # Landmarks
            if det.landmarks is not None:
                for lm in det.landmarks[:5]:
                    cv2.circle(vis, (int(lm[0]), int(lm[1])), 3, (255, 0, 0), -1)

            # Info overlay
            info = (
                f"conf:{det.confidence:.2f} "
                f"blur:{det.blur_score:.0f} "
                f"q:{det.quality_score:.2f}"
            )
            cv2.putText(vis, info, (x1, y1 - 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        return vis
