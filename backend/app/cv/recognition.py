"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  CV MODULE 4: FACE RECOGNITION & EMBEDDING MANAGEMENT                      ║
║                                                                              ║
║  Uses ArcFace (InsightFace buffalo_l model) for 512-dimensional            ║
║  face embeddings. Recognition pipeline:                                     ║
║                                                                              ║
║  Enrollment:                                                                 ║
║    1. Detect + align face from enrollment photo                             ║
║    2. Apply full filter pipeline                                             ║
║    3. Extract ArcFace embedding (512-d float32 vector)                      ║
║    4. Store embedding as .npy file                                          ║
║    5. Build/update FAISS index for fast similarity search                   ║
║                                                                              ║
║  Recognition:                                                                ║
║    1. Detect + align face from query frame                                  ║
║    2. Apply filter pipeline                                                  ║
║    3. Extract embedding                                                      ║
║    4. FAISS cosine similarity search against enrolled embeddings            ║
║    5. Return best match + confidence score                                  ║
║                                                                              ║
║  FAISS (Facebook AI Similarity Search) enables sub-millisecond lookup       ║
║  even with thousands of enrolled students.                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import cv2
import numpy as np
import os
import json
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

from app.cv.filters import ImageFilterPipeline, FilterConfig
from app.cv.face_detection import FaceDetector

logger = logging.getLogger(__name__)


@dataclass
class RecognitionResult:
    matched: bool
    student_id: Optional[str]
    similarity_score: float          # Cosine similarity 0–1
    threshold_used: float
    embedding_dim: int = 512
    fallback_used: bool = False      # True if FAISS wasn't available


class FaceRecognizer:
    """
    ArcFace-based face recognition with FAISS embedding index.

    Enrollment directory structure:
        uploads/faces/
            embeddings/
                student-001.npy     ← 512-d ArcFace embedding
                student-002.npy
            images/
                student-001.jpg     ← Enrollment face image
            index.json              ← student_id → embedding file mapping
    """

    EMBEDDING_DIR = "uploads/faces/embeddings"
    IMAGE_DIR = "uploads/faces/images"
    INDEX_FILE = "uploads/faces/index.json"
    EMBEDDING_DIM = 512

    def __init__(self, similarity_threshold: float = 0.55):
        self.threshold = similarity_threshold
        self.filter_pipeline = ImageFilterPipeline(FilterConfig())
        self.detector = FaceDetector()
        self.insightface_app = None
        self.faiss_index = None
        self.faiss_student_ids = []      # Parallel list: faiss_index[i] → student_id
        self._embeddings_cache = {}       # student_id → embedding (in-memory)

        os.makedirs(self.EMBEDDING_DIR, exist_ok=True)
        os.makedirs(self.IMAGE_DIR, exist_ok=True)

        self._init_insightface()
        self._load_index()
        self._build_faiss_index()

    # ─────────────────────────────────────────────────────────────────────────
    # Initialization
    # ─────────────────────────────────────────────────────────────────────────

    def _init_insightface(self):
        try:
            from insightface.app import FaceAnalysis
            self.insightface_app = FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"],
            )
            self.insightface_app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("[FaceRecognizer] InsightFace (ArcFace buffalo_l) loaded ✓")
        except Exception as e:
            logger.warning(f"[FaceRecognizer] InsightFace unavailable: {e}. Will use fallback embeddings.")

    def _load_index(self):
        """Load student_id → embedding mapping from disk."""
        if not os.path.exists(self.INDEX_FILE):
            self._save_index({})
            return

        with open(self.INDEX_FILE, "r") as f:
            index = json.load(f)

        for student_id, info in index.items():
            emb_path = info.get("embedding_path")
            if emb_path and os.path.exists(emb_path):
                emb = np.load(emb_path)
                self._embeddings_cache[student_id] = emb
                logger.debug(f"[FaceRecognizer] Loaded embedding for {student_id}")

        logger.info(f"[FaceRecognizer] Loaded {len(self._embeddings_cache)} embeddings from index")

    def _save_index(self, index: dict):
        with open(self.INDEX_FILE, "w") as f:
            json.dump(index, f, indent=2)

    def _build_faiss_index(self):
        """Build FAISS flat L2 index from all loaded embeddings."""
        if not self._embeddings_cache:
            return

        try:
            import faiss
            self.faiss_index = faiss.IndexFlatIP(self.EMBEDDING_DIM)  # Inner product = cosine if normalized
            embeddings = []
            self.faiss_student_ids = []

            for student_id, emb in self._embeddings_cache.items():
                # Normalize to unit vector for cosine similarity via inner product
                norm = np.linalg.norm(emb)
                if norm > 0:
                    embeddings.append(emb / norm)
                    self.faiss_student_ids.append(student_id)

            if embeddings:
                matrix = np.vstack(embeddings).astype(np.float32)
                self.faiss_index.add(matrix)
                logger.info(f"[FaceRecognizer] FAISS index built with {len(embeddings)} vectors")

        except ImportError:
            logger.warning("[FaceRecognizer] FAISS not available — will use numpy brute-force search")

    # ─────────────────────────────────────────────────────────────────────────
    # Enrollment
    # ─────────────────────────────────────────────────────────────────────────

    def enroll_student(
        self,
        student_id: str,
        face_image: np.ndarray,
    ) -> Tuple[bool, str]:
        """
        Enroll a student's face.

        1. Detect face in image
        2. Apply filter pipeline
        3. Extract ArcFace embedding
        4. Save embedding + image to disk
        5. Rebuild FAISS index

        Returns:
            (success: bool, message: str)
        """
        # Detect face
        detections = self.detector.detect(face_image)
        if not detections:
            return False, "No face detected in enrollment image"

        best_face = self.detector.get_best_face(detections)
        if best_face is None or best_face.face_crop is None:
            return False, "Face quality too low for enrollment"

        # Extract embedding
        embedding = self._extract_embedding(best_face.face_crop)
        if embedding is None:
            return False, "Failed to extract face embedding"

        # Save embedding
        emb_path = os.path.join(self.EMBEDDING_DIR, f"{student_id}.npy")
        np.save(emb_path, embedding)

        # Save face image
        img_path = os.path.join(self.IMAGE_DIR, f"{student_id}.jpg")
        cv2.imwrite(img_path, best_face.face_crop)

        # Update index file
        index = self._read_index()
        index[student_id] = {
            "embedding_path": emb_path,
            "image_path": img_path,
        }
        self._save_index(index)

        # Update in-memory cache
        self._embeddings_cache[student_id] = embedding

        # Rebuild FAISS
        self._build_faiss_index()

        logger.info(f"[FaceRecognizer] Enrolled student {student_id} ✓")
        return True, "Enrollment successful"

    def _read_index(self) -> dict:
        if not os.path.exists(self.INDEX_FILE):
            return {}
        with open(self.INDEX_FILE, "r") as f:
            return json.load(f)

    # ─────────────────────────────────────────────────────────────────────────
    # Recognition
    # ─────────────────────────────────────────────────────────────────────────

    def recognize(self, face_image: np.ndarray) -> RecognitionResult:
        """
        Identify a person from a face image.

        Returns RecognitionResult with matched student_id and similarity score.
        """
        if not self._embeddings_cache:
            return RecognitionResult(
                matched=False,
                student_id=None,
                similarity_score=0.0,
                threshold_used=self.threshold,
            )

        # Detect face
        detections = self.detector.detect(face_image)
        if not detections:
            return RecognitionResult(False, None, 0.0, self.threshold)

        best_face = self.detector.get_best_face(detections)
        if best_face is None or best_face.face_crop is None:
            return RecognitionResult(False, None, 0.0, self.threshold)

        # Extract embedding
        query_embedding = self._extract_embedding(best_face.face_crop)
        if query_embedding is None:
            return RecognitionResult(False, None, 0.0, self.threshold)

        # Search
        if self.faiss_index is not None and len(self.faiss_student_ids) > 0:
            return self._search_faiss(query_embedding)
        else:
            return self._search_numpy(query_embedding)

    def _extract_embedding(self, face_crop: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract 512-d ArcFace embedding from a face crop.
        Falls back to PCA-compressed HOG descriptor if InsightFace unavailable.
        """
        if self.insightface_app is not None:
            try:
                faces = self.insightface_app.get(face_crop)
                if faces:
                    emb = faces[0].embedding
                    return emb.astype(np.float32)
            except Exception as e:
                logger.error(f"InsightFace embedding error: {e}")

        # Fallback: HOG descriptor compressed to 512-d via random projection
        return self._hog_embedding_fallback(face_crop)

    def _hog_embedding_fallback(self, face_crop: np.ndarray) -> np.ndarray:
        """
        Fallback embedding using HOG (Histogram of Oriented Gradients).

        HOG is a classical CV descriptor that captures shape and texture.
        We project it to 512-d using a fixed random matrix (sketch embedding).
        Not as accurate as ArcFace but demonstrates the pipeline.
        """
        # Apply filter pipeline first
        result = self.filter_pipeline.process(face_crop)
        processed = result["processed"]

        # Compute HOG
        gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (64, 64))

        # Manual HOG computation
        gx = cv2.Sobel(resized.astype(np.float32), cv2.CV_32F, 1, 0, ksize=1)
        gy = cv2.Sobel(resized.astype(np.float32), cv2.CV_32F, 0, 1, ksize=1)
        magnitude, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)

        # Create HOG histogram (8x8 cells, 9 bins)
        cell_size = 8
        n_bins = 9
        cells_y = resized.shape[0] // cell_size
        cells_x = resized.shape[1] // cell_size
        hog_features = []

        for cy in range(cells_y):
            for cx in range(cells_x):
                cell_mag = magnitude[cy*cell_size:(cy+1)*cell_size, cx*cell_size:(cx+1)*cell_size]
                cell_ang = angle[cy*cell_size:(cy+1)*cell_size, cx*cell_size:(cx+1)*cell_size] % 180
                hist, _ = np.histogram(cell_ang, bins=n_bins, range=(0, 180), weights=cell_mag)
                hog_features.extend(hist.tolist())

        hog_vec = np.array(hog_features, dtype=np.float32)

        # Random projection to 512-d (fixed seed for reproducibility)
        rng = np.random.RandomState(42)
        projection_matrix = rng.randn(len(hog_vec), self.EMBEDDING_DIM).astype(np.float32)
        projection_matrix /= np.linalg.norm(projection_matrix, axis=0, keepdims=True)

        embedding = hog_vec @ projection_matrix
        norm = np.linalg.norm(embedding)
        return embedding / (norm + 1e-8)

    def _search_faiss(self, query_embedding: np.ndarray) -> RecognitionResult:
        """Search FAISS index for nearest neighbor."""
        # Normalize query
        norm = np.linalg.norm(query_embedding)
        query_norm = (query_embedding / (norm + 1e-8)).reshape(1, -1).astype(np.float32)

        # Search (top-1)
        scores, indices = self.faiss_index.search(query_norm, 1)
        similarity = float(scores[0][0])
        idx = int(indices[0][0])

        if idx < 0 or idx >= len(self.faiss_student_ids):
            return RecognitionResult(False, None, similarity, self.threshold)

        student_id = self.faiss_student_ids[idx]
        matched = similarity >= self.threshold

        return RecognitionResult(
            matched=matched,
            student_id=student_id if matched else None,
            similarity_score=similarity,
            threshold_used=self.threshold,
        )

    def _search_numpy(self, query_embedding: np.ndarray) -> RecognitionResult:
        """Brute-force cosine similarity search (fallback without FAISS)."""
        best_score = -1.0
        best_student_id = None

        q_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        for student_id, emb in self._embeddings_cache.items():
            e_norm = emb / (np.linalg.norm(emb) + 1e-8)
            similarity = float(np.dot(q_norm, e_norm))
            if similarity > best_score:
                best_score = similarity
                best_student_id = student_id

        matched = best_score >= self.threshold

        return RecognitionResult(
            matched=matched,
            student_id=best_student_id if matched else None,
            similarity_score=best_score,
            threshold_used=self.threshold,
            fallback_used=True,
        )

    def remove_enrollment(self, student_id: str) -> bool:
        """Remove a student's enrollment data."""
        index = self._read_index()
        if student_id not in index:
            return False

        info = index.pop(student_id)
        for path_key in ["embedding_path", "image_path"]:
            path = info.get(path_key)
            if path and os.path.exists(path):
                os.remove(path)

        self._save_index(index)
        self._embeddings_cache.pop(student_id, None)
        self._build_faiss_index()
        return True
