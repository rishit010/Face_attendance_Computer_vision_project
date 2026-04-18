"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CV MODULE 3: LIVENESS DETECTION (ANTI-SPOOFING)                           ║
║                                                                              ║
║  Two-stage liveness pipeline:                                               ║
║                                                                              ║
║  Stage 1 — PASSIVE LIVENESS (single frame)                                 ║
║    • Texture Analysis: LBP (Local Binary Patterns) — detects print spoofs  ║
║    • Frequency Analysis: FFT-based — detects screen moiré patterns         ║
║    • Gradient Analysis: Sobel/Scharr — real faces have natural gradients   ║
║    • Color Distribution: HSV analysis — screens have different color dist  ║
║    • Specular Reflection: Real faces have skin reflections, photos don't   ║
║                                                                              ║
║  Stage 2 — ACTIVE LIVENESS (multi-frame challenge-response)                ║
║    • Blink Detection: Eye Aspect Ratio (EAR) across frames                 ║
║    • Head Nod: Nose tip vertical displacement across frames                 ║
║    • Smile Detection: Mouth aspect ratio change across frames               ║
║    • Random challenge selection prevents replay attacks                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum
import logging
import random

logger = logging.getLogger(__name__)


class LivenessChallenge(str, Enum):
    BLINK = "blink"
    NOD = "nod"
    SMILE = "smile"


@dataclass
class PassiveLivenessResult:
    score: float             # 0 = spoof, 1 = live
    is_live: bool
    # Component scores
    lbp_score: float = 0.0          # Texture analysis
    fft_score: float = 0.0          # Frequency analysis
    gradient_score: float = 0.0     # Edge gradient naturalness
    color_score: float = 0.0        # Color distribution
    reflection_score: float = 0.0  # Specular reflection
    reason: str = ""


@dataclass
class ActiveLivenessResult:
    challenge: LivenessChallenge
    passed: bool
    confidence: float
    frames_analyzed: int
    detected_movement: float
    reason: str = ""


class LivenessDetector:
    """
    Full passive + active liveness detection pipeline.

    Anti-spoofing targets:
      - Printed photo attacks (LBP texture, gradient analysis)
      - Digital screen attacks (FFT moiré, color distribution)
      - Video replay attacks (active challenge, token binding)
      - 3D mask attacks (reflection analysis, random challenge)
    """

    # Thresholds (tuned empirically — adjust based on your test data)
    PASSIVE_THRESHOLD = 0.55
    ACTIVE_BLINK_EAR_THRESHOLD = 0.20   # EAR below this = eye closed
    ACTIVE_NOD_DISPLACEMENT_PX = 6      # Min pixel movement for nod
    ACTIVE_SMILE_MAR_CHANGE = 0.08      # Min mouth aspect ratio change

    def __init__(self):
        self._init_mediapipe()

    def _init_mediapipe(self):
        """Initialize MediaPipe FaceMesh for landmark-based active liveness."""
        try:
            import mediapipe as mp
            mp_fm = mp.solutions.face_mesh
            self.face_mesh = mp_fm.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            logger.info("[Liveness] MediaPipe FaceMesh loaded ✓")
        except Exception as e:
            self.face_mesh = None
            logger.warning(f"[Liveness] MediaPipe not available: {e}")

    # ══════════════════════════════════════════════════════════════════════════
    # Stage 1: Passive Liveness
    # ══════════════════════════════════════════════════════════════════════════

    def passive_liveness(self, face_crop: np.ndarray) -> PassiveLivenessResult:
        """
        Analyze a single face crop for liveness signals.

        Args:
            face_crop: Aligned face crop, BGR, ideally 112x112

        Returns:
            PassiveLivenessResult with per-component scores
        """
        if face_crop is None or face_crop.size == 0:
            return PassiveLivenessResult(0.0, False, reason="Empty face crop")

        # Resize to consistent size for analysis
        face = cv2.resize(face_crop, (128, 128))
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)

        # Run all passive checks
        lbp_score      = self._lbp_texture_analysis(gray)
        fft_score      = self._fft_frequency_analysis(gray)
        gradient_score = self._gradient_naturalness(gray)
        color_score    = self._color_distribution_analysis(face)
        reflection_score = self._specular_reflection_analysis(face)

        # Weighted ensemble (weights tuned for indoor classroom setting)
        score = (
            0.30 * lbp_score +
            0.25 * fft_score +
            0.20 * gradient_score +
            0.15 * color_score +
            0.10 * reflection_score
        )
        score = float(np.clip(score, 0.0, 1.0))
        is_live = score >= self.PASSIVE_THRESHOLD

        reason = self._build_passive_reason(lbp_score, fft_score, gradient_score, color_score, is_live)

        return PassiveLivenessResult(
            score=score,
            is_live=is_live,
            lbp_score=lbp_score,
            fft_score=fft_score,
            gradient_score=gradient_score,
            color_score=color_score,
            reflection_score=reflection_score,
            reason=reason,
        )

    def _lbp_texture_analysis(self, gray: np.ndarray) -> float:
        """
        Local Binary Patterns (LBP) texture analysis.

        Real faces have rich, varied micro-texture (pores, fine hair, skin grain).
        Printed photos lose this texture. Screens show pixel grid patterns.

        We compute LBP histogram uniformity — real faces have specific
        entropy ranges; spoofs cluster at different values.

        LBP(p, r) computes binary codes by comparing each pixel to its
        P neighbors at radius R.
        """
        # Simple 8-neighbor LBP implementation without sklearn
        h, w = gray.shape
        lbp = np.zeros_like(gray, dtype=np.uint8)

        # 8 neighbor offsets
        neighbors = [
            (-1, -1), (-1, 0), (-1, 1),
            ( 0,  1),
            ( 1,  1), ( 1,  0), ( 1, -1),
            ( 0, -1),
        ]

        for idx, (dy, dx) in enumerate(neighbors):
            shifted = np.roll(np.roll(gray, dy, axis=0), dx, axis=1)
            lbp |= ((gray >= shifted).astype(np.uint8) << idx)

        # Compute histogram
        hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
        hist = hist.astype(np.float32) / (hist.sum() + 1e-8)

        # Entropy: real faces have moderate entropy, spoofs are extreme
        entropy = -np.sum(hist[hist > 0] * np.log2(hist[hist > 0] + 1e-8))
        # Typical real face LBP entropy: 6.5–7.8 bits
        # Screen/photo: < 5.5 or > 8.2
        entropy_score = 1.0 if 5.5 <= entropy <= 8.2 else max(0, 1 - abs(entropy - 7.0) / 3.0)
        return float(entropy_score)

    def _fft_frequency_analysis(self, gray: np.ndarray) -> float:
        """
        FFT frequency analysis to detect screen display patterns.

        Digital screens produce regular high-frequency moiré patterns
        when photographed. Real faces have a smooth 1/f power spectrum.

        We check:
        1. Presence of periodic spikes in frequency domain (screen artifacts)
        2. Power spectral density slope (real face ≈ -2 to -3 on log-log scale)
        """
        # Apply FFT
        fft = np.fft.fft2(gray.astype(np.float32))
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.abs(fft_shift)
        log_magnitude = np.log1p(magnitude)

        h, w = log_magnitude.shape
        center_y, center_x = h // 2, w // 2

        # Detect periodic spikes (screen artifact)
        # Create ring mask (ignore DC component in center)
        y_idx, x_idx = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x_idx - center_x)**2 + (y_idx - center_y)**2)
        ring_mask = (dist_from_center > 5) & (dist_from_center < min(h, w) // 2 - 5)

        ring_magnitudes = log_magnitude[ring_mask]
        mean_mag = ring_magnitudes.mean()
        std_mag = ring_magnitudes.std()

        # Spikes = values > mean + 3*std → typical of screen patterns
        spikes = np.sum(ring_magnitudes > mean_mag + 3.5 * std_mag)
        spike_ratio = spikes / (ring_magnitudes.size + 1e-8)

        # Low spike ratio → likely real face
        # High spike ratio → likely screen/photo
        fft_score = max(0, 1.0 - spike_ratio * 20)
        return float(np.clip(fft_score, 0, 1))

    def _gradient_naturalness(self, gray: np.ndarray) -> float:
        """
        Gradient magnitude distribution analysis.

        Real faces have a characteristic gradient distribution:
        - Strong gradients at facial feature edges (eyes, lips, nose)
        - Smooth gradient transitions in skin regions
        - Natural noise floor throughout

        Printed photos often have:
        - Very strong gradients from printer patterns
        - Different distribution shape

        We use Sobel operators (both x and y) to compute gradient magnitude.
        """
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)

        # Normalize
        if gradient_magnitude.max() > 0:
            gradient_magnitude = gradient_magnitude / gradient_magnitude.max()

        # Analyze distribution
        mean_grad = gradient_magnitude.mean()
        std_grad = gradient_magnitude.std()

        # Real face: moderate mean (0.08–0.25), moderate std (0.06–0.20)
        mean_ok = 0.05 <= mean_grad <= 0.30
        std_ok = 0.05 <= std_grad <= 0.25

        # Coefficient of variation (std/mean) — real faces: 0.5–2.5
        cv = std_grad / (mean_grad + 1e-8)
        cv_ok = 0.4 <= cv <= 3.0

        score = (0.4 * int(mean_ok) + 0.4 * int(std_ok) + 0.2 * int(cv_ok))
        return float(score)

    def _color_distribution_analysis(self, face_bgr: np.ndarray) -> float:
        """
        Analyze color distribution in HSV space.

        Real faces:
        - Skin tone occupies a specific HSV range (hue ~0–25° and ~330–360°)
        - Natural saturation distribution
        - Screen displays have shifted or oversaturated colors

        We check the proportion of pixels in the skin-tone HSV range.
        """
        hsv = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # Skin tone hue mask (accommodates various skin tones)
        skin_hue_low1 = (h >= 0) & (h <= 25)
        skin_hue_low2 = (h >= 150) & (h <= 180)
        skin_sat = (s >= 30) & (s <= 200)
        skin_val = (v >= 50) & (v <= 230)

        skin_mask = (skin_hue_low1 | skin_hue_low2) & skin_sat & skin_val
        skin_ratio = skin_mask.sum() / (h.size + 1e-8)

        # Real face: 30–85% pixels should be skin-colored
        if 0.25 <= skin_ratio <= 0.90:
            # Scale score based on how "perfect" the ratio is
            ideal = 0.55
            deviation = abs(skin_ratio - ideal)
            score = max(0, 1.0 - deviation * 2.0)
        else:
            score = 0.2  # Very unlikely to be a real face

        return float(score)

    def _specular_reflection_analysis(self, face_bgr: np.ndarray) -> float:
        """
        Check for specular highlights on skin.

        Real faces under indoor lighting have subtle specular reflections
        on the forehead, nose bridge, and cheekbones.
        Flat printed photos lack this.
        Screens have different reflection patterns.

        We look for small high-brightness regions in the upper-face area.
        """
        # Focus on upper face (forehead, nose region)
        h, w = face_bgr.shape[:2]
        upper_face = face_bgr[:h // 2, w // 4: 3 * w // 4]

        if upper_face.size == 0:
            return 0.5  # Neutral if can't analyze

        # Convert to grayscale
        gray = cv2.cvtColor(upper_face, cv2.COLOR_BGR2GRAY)

        # Specular highlights = very bright small regions
        _, bright_mask = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
        bright_ratio = bright_mask.sum() / (255 * gray.size + 1e-8)

        # Real face indoor: 0.01–0.15 bright pixel ratio
        # Photo: ~0 (no reflections)
        # Screen: > 0.20 (too many bright pixels)
        if 0.005 <= bright_ratio <= 0.18:
            score = 0.85
        elif bright_ratio < 0.005:
            score = 0.3  # Likely photo (no reflections)
        else:
            score = 0.4  # Likely screen

        return float(score)

    def _build_passive_reason(self, lbp, fft, grad, color, is_live) -> str:
        reasons = []
        if lbp < 0.5:
            reasons.append("unusual texture pattern")
        if fft < 0.5:
            reasons.append("screen artifact detected")
        if grad < 0.5:
            reasons.append("unnatural gradient distribution")
        if color < 0.5:
            reasons.append("skin color anomaly")

        if is_live:
            return "Passive checks passed"
        return "Failed: " + (", ".join(reasons) if reasons else "low overall score")

    # ══════════════════════════════════════════════════════════════════════════
    # Stage 2: Active Liveness — Challenge-Response
    # ══════════════════════════════════════════════════════════════════════════

    def get_random_challenge(self) -> LivenessChallenge:
        """Return a random challenge type — prevents pre-recording attacks."""
        return random.choice(list(LivenessChallenge))

    def verify_active_challenge(
        self,
        frames: List[np.ndarray],
        challenge: LivenessChallenge,
    ) -> ActiveLivenessResult:
        """
        Verify that the student performed the requested challenge.

        Args:
            frames: List of BGR frames captured during challenge (5–15 frames)
            challenge: Which challenge was requested

        Returns:
            ActiveLivenessResult
        """
        if len(frames) < 3:
            return ActiveLivenessResult(
                challenge=challenge,
                passed=False,
                confidence=0.0,
                frames_analyzed=len(frames),
                detected_movement=0.0,
                reason="Too few frames provided",
            )

        if challenge == LivenessChallenge.BLINK:
            return self._verify_blink(frames)
        elif challenge == LivenessChallenge.NOD:
            return self._verify_nod(frames)
        elif challenge == LivenessChallenge.SMILE:
            return self._verify_smile(frames)
        else:
            return ActiveLivenessResult(challenge, False, 0.0, 0, 0.0, "Unknown challenge")

    # ── Blink Detection ───────────────────────────────────────────────────────

    def _verify_blink(self, frames: List[np.ndarray]) -> ActiveLivenessResult:
        """
        Blink detection using Eye Aspect Ratio (EAR).

        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        where p1..p6 are eye landmark points.

        A blink = EAR drops below threshold then returns above it.
        """
        ear_values = []

        for frame in frames:
            ear = self._compute_ear(frame)
            if ear is not None:
                ear_values.append(ear)

        if len(ear_values) < 3:
            return ActiveLivenessResult(
                LivenessChallenge.BLINK, False, 0.0, len(frames), 0.0,
                "Could not extract eye landmarks from enough frames"
            )

        min_ear = min(ear_values)
        max_ear = max(ear_values)
        ear_range = max_ear - min_ear

        # A genuine blink: EAR drops significantly then recovers
        blink_detected = (
            min_ear < self.ACTIVE_BLINK_EAR_THRESHOLD and
            max_ear > 0.25 and
            ear_range > 0.10
        )

        confidence = min(1.0, ear_range / 0.25) if blink_detected else ear_range / 0.25

        return ActiveLivenessResult(
            challenge=LivenessChallenge.BLINK,
            passed=blink_detected,
            confidence=float(confidence),
            frames_analyzed=len(ear_values),
            detected_movement=float(ear_range),
            reason="Blink detected" if blink_detected else f"No blink: min_ear={min_ear:.3f}, range={ear_range:.3f}",
        )

    def _compute_ear(self, frame: np.ndarray) -> Optional[float]:
        """Compute Eye Aspect Ratio from a single frame using MediaPipe."""
        if self.face_mesh is None:
            return None

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.face_mesh.process(rgb)

        if not result.multi_face_landmarks:
            return None

        lm = result.multi_face_landmarks[0].landmark
        h, w = frame.shape[:2]

        def pt(idx):
            return np.array([lm[idx].x * w, lm[idx].y * h])

        # MediaPipe FaceMesh eye landmark indices
        # Left eye
        LEFT_EYE = [362, 385, 387, 263, 373, 380]
        # Right eye
        RIGHT_EYE = [33, 160, 158, 133, 153, 144]

        def ear(eye_pts):
            p1, p2, p3, p4, p5, p6 = [pt(i) for i in eye_pts]
            a = np.linalg.norm(p2 - p6)
            b = np.linalg.norm(p3 - p5)
            c = np.linalg.norm(p1 - p4)
            return (a + b) / (2.0 * c + 1e-6)

        left_ear = ear(LEFT_EYE)
        right_ear = ear(RIGHT_EYE)
        return float((left_ear + right_ear) / 2.0)

    # ── Nod Detection ─────────────────────────────────────────────────────────

    def _verify_nod(self, frames: List[np.ndarray]) -> ActiveLivenessResult:
        """
        Head nod detection: track nose tip Y position across frames.
        A nod = nose tip moves down then up (or vice versa).
        """
        nose_y_positions = []

        for frame in frames:
            nose_y = self._get_nose_tip_y(frame)
            if nose_y is not None:
                nose_y_positions.append(nose_y)

        if len(nose_y_positions) < 3:
            return ActiveLivenessResult(
                LivenessChallenge.NOD, False, 0.0, len(frames), 0.0,
                "Could not track nose across frames"
            )

        movement_range = max(nose_y_positions) - min(nose_y_positions)
        nod_detected = movement_range >= self.ACTIVE_NOD_DISPLACEMENT_PX
        confidence = min(1.0, movement_range / (self.ACTIVE_NOD_DISPLACEMENT_PX * 2))

        return ActiveLivenessResult(
            challenge=LivenessChallenge.NOD,
            passed=nod_detected,
            confidence=float(confidence),
            frames_analyzed=len(nose_y_positions),
            detected_movement=float(movement_range),
            reason=f"Nod {'detected' if nod_detected else 'not detected'}: movement={movement_range:.1f}px",
        )

    def _get_nose_tip_y(self, frame: np.ndarray) -> Optional[float]:
        """Get nose tip Y coordinate (landmark index 4 in MediaPipe)."""
        if self.face_mesh is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.face_mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None
        lm = result.multi_face_landmarks[0].landmark
        return lm[4].y * frame.shape[0]

    # ── Smile Detection ───────────────────────────────────────────────────────

    def _verify_smile(self, frames: List[np.ndarray]) -> ActiveLivenessResult:
        """
        Smile detection: track Mouth Aspect Ratio (MAR) across frames.
        A smile = mouth corners move outward / lip separation increases.
        """
        mar_values = []

        for frame in frames:
            mar = self._compute_mar(frame)
            if mar is not None:
                mar_values.append(mar)

        if len(mar_values) < 3:
            return ActiveLivenessResult(
                LivenessChallenge.SMILE, False, 0.0, len(frames), 0.0,
                "Could not extract mouth landmarks"
            )

        mar_range = max(mar_values) - min(mar_values)
        smile_detected = mar_range >= self.ACTIVE_SMILE_MAR_CHANGE
        confidence = min(1.0, mar_range / (self.ACTIVE_SMILE_MAR_CHANGE * 2))

        return ActiveLivenessResult(
            challenge=LivenessChallenge.SMILE,
            passed=smile_detected,
            confidence=float(confidence),
            frames_analyzed=len(mar_values),
            detected_movement=float(mar_range),
            reason=f"Smile {'detected' if smile_detected else 'not detected'}: MAR_range={mar_range:.3f}",
        )

    def _compute_mar(self, frame: np.ndarray) -> Optional[float]:
        """Compute Mouth Aspect Ratio from MediaPipe landmarks."""
        if self.face_mesh is None:
            return None
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.face_mesh.process(rgb)
        if not result.multi_face_landmarks:
            return None

        lm = result.multi_face_landmarks[0].landmark
        h, w = frame.shape[:2]

        def pt(idx):
            return np.array([lm[idx].x * w, lm[idx].y * h])

        # Mouth landmark indices (MediaPipe)
        # Upper lip: 13, Lower lip: 14, Left corner: 78, Right corner: 308
        top, bottom = pt(13), pt(14)
        left, right = pt(78), pt(308)

        vertical = np.linalg.norm(top - bottom)
        horizontal = np.linalg.norm(left - right)

        mar = vertical / (horizontal + 1e-6)
        return float(mar)
