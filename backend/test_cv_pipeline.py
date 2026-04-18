"""
Quick smoke test for the CV pipeline.
Run this to verify all modules import correctly before starting the server.

Usage (from backend/ with venv active):
    python test_cv_pipeline.py
"""

import sys
import numpy as np

print("=" * 55)
print("  Face Attendance System — CV Pipeline Smoke Test")
print("=" * 55)


def test(label: str, fn):
    try:
        fn()
        print(f"  ✓  {label}")
        return True
    except Exception as e:
        print(f"  ✗  {label}  →  {e}")
        return False


results = []

# ── Imports ───────────────────────────────────────────────────────────────────
print("\n[1] Checking imports...")
results.append(test("OpenCV", lambda: __import__("cv2")))
results.append(test("NumPy", lambda: __import__("numpy")))
results.append(test("FastAPI", lambda: __import__("fastapi")))
results.append(test("SQLModel", lambda: __import__("sqlmodel")))
results.append(test("InsightFace", lambda: __import__("insightface")))
results.append(test("MediaPipe", lambda: __import__("mediapipe")))
results.append(test("FAISS", lambda: __import__("faiss")))

# ── CV Modules ────────────────────────────────────────────────────────────────
print("\n[2] Loading CV modules...")

def test_filters():
    from app.cv.filters import ImageFilterPipeline, FilterConfig
    pipeline = ImageFilterPipeline(FilterConfig())
    dummy = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    out = pipeline.process(dummy)
    assert "processed" in out
    assert out["processed"].shape == (112, 112, 3)

def test_detection():
    from app.cv.face_detection import FaceDetector
    detector = FaceDetector()
    assert detector.haar_cascade is not None or detector.insightface_model is not None

def test_liveness():
    from app.cv.liveness import LivenessDetector
    detector = LivenessDetector()
    dummy = np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)
    result = detector.passive_liveness(dummy)
    assert 0.0 <= result.score <= 1.0

def test_recognition():
    from app.cv.recognition import FaceRecognizer
    rec = FaceRecognizer()
    dummy = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    emb = rec._hog_embedding_fallback(dummy)
    assert emb.shape == (512,)

results.append(test("Filter pipeline", test_filters))
results.append(test("Face detector init", test_detection))
results.append(test("Liveness detector", test_liveness))
results.append(test("Face recognizer + HOG fallback", test_recognition))

# ── Geofence ──────────────────────────────────────────────────────────────────
print("\n[3] Geofence check...")

def test_geofence():
    from app.core.geofence import GeoPoint, haversine_distance, is_within_radius
    p1 = GeoPoint(26.9124, 75.7873)
    p2 = GeoPoint(26.9125, 75.7874)
    d = haversine_distance(p1, p2)
    assert 0 < d < 50  # Should be ~14m
    inside, dist = is_within_radius(p2, p1, 20.0)
    assert inside

results.append(test("Haversine geofence", test_geofence))

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 55)
passed = sum(results)
total = len(results)
print(f"  Result: {passed}/{total} checks passed")
if passed == total:
    print("  ✅  All good — run: uvicorn app.main:app --reload")
else:
    print("  ⚠   Some checks failed — check missing dependencies above")
print("=" * 55)
