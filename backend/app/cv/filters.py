"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CV MODULE 1: IMAGE PREPROCESSING & FILTERS                                ║
║                                                                              ║
║  This module applies a full classical CV filter pipeline to every frame     ║
║  before it reaches the neural network. Filters serve multiple purposes:     ║
║  - Noise reduction (Gaussian, bilateral, median)                             ║
║  - Contrast enhancement (CLAHE, histogram equalization)                     ║
║  - Edge sharpening for better facial landmark detection                     ║
║  - Normalization for consistent embedding quality                           ║
║  - Illumination compensation for varying classroom lighting                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """
    Fine-grained control over every filter in the pipeline.
    Defaults are tuned for face recognition in indoor classroom lighting.
    """
    # ── Noise Reduction ──────────────────────────────────────────────────────
    apply_gaussian_blur: bool = True
    gaussian_kernel_size: Tuple[int, int] = (3, 3)    # Small kernel — preserve edges
    gaussian_sigma: float = 0.8

    apply_bilateral_filter: bool = True                # Edge-preserving denoising
    bilateral_d: int = 9                               # Neighbourhood diameter
    bilateral_sigma_color: float = 75                  # Color space sigma
    bilateral_sigma_space: float = 75                  # Coordinate space sigma

    apply_median_blur: bool = False                    # Useful for salt & pepper noise
    median_kernel_size: int = 3

    # ── Contrast & Illumination ───────────────────────────────────────────────
    apply_clahe: bool = True                           # Contrast Limited Adaptive HE
    clahe_clip_limit: float = 2.0                      # Higher = more contrast boost
    clahe_tile_grid_size: Tuple[int, int] = (8, 8)     # Local region size

    apply_gamma_correction: bool = True
    gamma: float = 1.1                                 # > 1 brightens, < 1 darkens

    apply_histogram_equalization: bool = False         # Global HE (fallback to CLAHE)

    # ── Sharpening ───────────────────────────────────────────────────────────
    apply_unsharp_mask: bool = True                    # Unsharp masking for detail
    unsharp_strength: float = 0.6                      # 0 = no sharpen, 1 = max
    unsharp_blur_size: Tuple[int, int] = (5, 5)

    apply_laplacian_sharpen: bool = False              # Alternative: Laplacian sharpen

    # ── Normalization ────────────────────────────────────────────────────────
    apply_face_normalization: bool = True              # Per-face mean/std normalize
    target_size: Tuple[int, int] = (112, 112)          # ArcFace standard input size

    # ── Debug ────────────────────────────────────────────────────────────────
    save_debug_stages: bool = False                    # Save intermediate filter stages


class ImageFilterPipeline:
    """
    Full classical CV preprocessing pipeline.

    Stages (in order):
      1. Decode & validate input
      2. Noise reduction (Gaussian → Bilateral)
      3. Illumination normalization (CLAHE on L channel of LAB)
      4. Gamma correction
      5. Unsharp masking (sharpening)
      6. Resize to target
      7. Per-face normalization

    The pipeline operates in LAB colour space for illumination handling
    and converts back to BGR/RGB for neural network input.
    """

    def __init__(self, config: Optional[FilterConfig] = None):
        self.cfg = config or FilterConfig()
        self._clahe = cv2.createCLAHE(
            clipLimit=self.cfg.clahe_clip_limit,
            tileGridSize=self.cfg.clahe_tile_grid_size,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def process(self, image: np.ndarray, debug: bool = False) -> dict:
        """
        Run the full filter pipeline on an image.

        Args:
            image: BGR numpy array (H, W, 3)
            debug: If True, return all intermediate stages

        Returns:
            dict with keys:
              'processed'     : final processed BGR image
              'normalized'    : float32 array normalized for neural net
              'stages'        : dict of intermediate images (if debug=True)
        """
        stages = {}
        img = image.copy()

        # Stage 0: Validate
        if img is None or img.size == 0:
            raise ValueError("Empty image passed to filter pipeline")
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        stages["00_input"] = img.copy()

        # Stage 1: Noise reduction
        img = self._apply_noise_reduction(img)
        stages["01_denoised"] = img.copy()

        # Stage 2: Illumination compensation (CLAHE in LAB space)
        img = self._apply_illumination_compensation(img)
        stages["02_illumination"] = img.copy()

        # Stage 3: Gamma correction
        if self.cfg.apply_gamma_correction:
            img = self._gamma_correct(img, self.cfg.gamma)
        stages["03_gamma"] = img.copy()

        # Stage 4: Sharpening
        img = self._apply_sharpening(img)
        stages["04_sharpened"] = img.copy()

        # Stage 5: Resize to ArcFace target (112x112)
        img = cv2.resize(img, self.cfg.target_size, interpolation=cv2.INTER_LANCZOS4)
        stages["05_resized"] = img.copy()

        # Stage 6: Per-face normalization (float32, mean/std)
        normalized = self._normalize(img)
        stages["06_normalized"] = (normalized * 255).astype(np.uint8)

        return {
            "processed": img,
            "normalized": normalized,
            "stages": stages if debug else {},
        }

    def process_batch(self, images: list[np.ndarray]) -> list[np.ndarray]:
        """Process multiple face crops in one call."""
        return [self.process(img)["normalized"] for img in images]

    # ─────────────────────────────────────────────────────────────────────────
    # Private: Filter implementations
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_noise_reduction(self, img: np.ndarray) -> np.ndarray:
        """Apply noise reduction filters in sequence."""

        if self.cfg.apply_gaussian_blur:
            img = cv2.GaussianBlur(
                img,
                self.cfg.gaussian_kernel_size,
                self.cfg.gaussian_sigma,
            )

        if self.cfg.apply_bilateral_filter:
            # Bilateral filter: edge-preserving — key for keeping facial features sharp
            img = cv2.bilateralFilter(
                img,
                self.cfg.bilateral_d,
                self.cfg.bilateral_sigma_color,
                self.cfg.bilateral_sigma_space,
            )

        if self.cfg.apply_median_blur:
            img = cv2.medianBlur(img, self.cfg.median_kernel_size)

        return img

    def _apply_illumination_compensation(self, img: np.ndarray) -> np.ndarray:
        """
        CLAHE on the L (lightness) channel of LAB color space.
        This is superior to global histogram equalization because:
          - Operates locally (tile-based) → handles shadows on face correctly
          - Doesn't over-amplify noise in uniform regions (clip limit)
          - Preserves colour information (operates only on L channel)
        """
        if not self.cfg.apply_clahe:
            return img

        # BGR → LAB
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # Apply CLAHE only to L channel
        l_equalized = self._clahe.apply(l_channel)

        # Merge back
        lab_equalized = cv2.merge([l_equalized, a_channel, b_channel])
        result = cv2.cvtColor(lab_equalized, cv2.COLOR_LAB2BGR)

        if self.cfg.apply_histogram_equalization and not self.cfg.apply_clahe:
            # Fallback: global histogram equalization (cruder alternative)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            equalized = cv2.equalizeHist(gray)
            result = cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR)

        return result

    def _gamma_correct(self, img: np.ndarray, gamma: float) -> np.ndarray:
        """
        Gamma correction to brighten/darken the image.
        Uses a lookup table (LUT) for fast per-pixel mapping.
        Useful when classroom lighting is too dark or over-exposed.
        """
        inv_gamma = 1.0 / gamma
        lut = np.array(
            [((i / 255.0) ** inv_gamma) * 255 for i in range(256)],
            dtype=np.uint8,
        )
        return cv2.LUT(img, lut)

    def _apply_sharpening(self, img: np.ndarray) -> np.ndarray:
        """Apply sharpening to enhance facial feature edges."""

        if self.cfg.apply_unsharp_mask:
            img = self._unsharp_mask(img)

        if self.cfg.apply_laplacian_sharpen:
            img = self._laplacian_sharpen(img)

        return img

    def _unsharp_mask(self, img: np.ndarray) -> np.ndarray:
        """
        Unsharp masking: sharpen = original + strength * (original - blurred)
        This enhances high-frequency details (edges, texture) — important
        for facial landmark quality and liveness texture analysis.
        """
        blurred = cv2.GaussianBlur(img, self.cfg.unsharp_blur_size, 0)
        sharpened = cv2.addWeighted(
            img, 1.0 + self.cfg.unsharp_strength,
            blurred, -self.cfg.unsharp_strength,
            0,
        )
        return sharpened

    def _laplacian_sharpen(self, img: np.ndarray) -> np.ndarray:
        """
        Laplacian sharpening kernel.
        Adds second-derivative edge response back to the image.
        """
        kernel = np.array([
            [ 0, -1,  0],
            [-1,  5, -1],
            [ 0, -1,  0],
        ], dtype=np.float32)
        return cv2.filter2D(img, -1, kernel)

    def _normalize(self, img: np.ndarray) -> np.ndarray:
        """
        Per-image mean/std normalization for neural network input.
        Result is float32 in range ~[-3, 3] (standardized).
        ArcFace models expect this normalization.
        """
        img_float = img.astype(np.float32) / 255.0
        mean = np.mean(img_float)
        std = np.std(img_float) + 1e-8  # Avoid division by zero
        normalized = (img_float - mean) / std
        return normalized

    # ─────────────────────────────────────────────────────────────────────────
    # Utility: Annotate image with filter info overlay
    # ─────────────────────────────────────────────────────────────────────────

    def draw_filter_debug_overlay(
        self, stages: dict, output_size: Tuple[int, int] = (800, 600)
    ) -> np.ndarray:
        """
        Create a grid image showing all filter stages side by side.
        Useful for debugging and CV course presentations.
        """
        if not stages:
            return np.zeros((*output_size[::-1], 3), dtype=np.uint8)

        n = len(stages)
        cols = 4
        rows = (n + cols - 1) // cols
        cell_h, cell_w = 200, 200
        canvas = np.zeros((rows * cell_h + rows * 30, cols * cell_w, 3), dtype=np.uint8)

        for idx, (name, stage_img) in enumerate(stages.items()):
            r, c = divmod(idx, cols)
            y_off = r * (cell_h + 30)
            x_off = c * cell_w

            if len(stage_img.shape) == 2:
                stage_img = cv2.cvtColor(stage_img, cv2.COLOR_GRAY2BGR)

            thumb = cv2.resize(stage_img, (cell_w, cell_h))
            canvas[y_off : y_off + cell_h, x_off : x_off + cell_w] = thumb
            cv2.putText(
                canvas, name, (x_off + 4, y_off + cell_h + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1,
            )

        return canvas
