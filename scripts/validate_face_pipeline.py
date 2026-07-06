import os
import sys
import cv2
from validation_assets import ensure_test_face

# Setup paths
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from face_pipeline import FacePipeline

TEST_IMAGE = os.path.join(CWD, "lena.jpg")

print("Starting face pipeline validation tests...")

# 1. Initialize FacePipeline
try:
    pipeline = FacePipeline()
    print("FacePipeline initialized successfully (models loaded).")
except Exception as e:
    print(f"Error initializing FacePipeline: {e}")
    sys.exit(1)

# 2. Check if test image exists, copy fixture if missing
try:
    created_test_image = ensure_test_face(TEST_IMAGE)
except Exception as e:
    print(f"Failed to prepare test image: {e}")
    sys.exit(1)

# 3. Read image
img = cv2.imread(TEST_IMAGE)
if img is None:
    print(f"Failed to read image at {TEST_IMAGE}")
    sys.exit(1)

print(f"Loaded test image: shape={img.shape}")

# 4. Perform face detection
faces = pipeline.detect_faces(img)
print(f"Detected {len(faces)} face(s).")

if len(faces) == 0:
    print("Assertion failed: No face detected in lena.jpg!")
    sys.exit(1)

# 5. Check first face bounding box and landmarks
first_face = faces[0]
bbox = first_face["bbox"]
landmarks = first_face["landmarks"]
score = first_face["score"]

print(f"Face bbox: {bbox}")
print(f"Face landmarks: {landmarks}")
print(f"Face detection confidence score: {score:.4f}")

assert len(bbox) == 4, "Bbox must contain 4 elements"
assert len(landmarks) == 5, "Must locate exactly 5 landmarks"
assert score >= 0.6, f"Confidence score too low: {score}"

# 6. Extract embedding
print("Extracting embedding vector...")
embedding = pipeline.extract_embedding(img, first_face["raw_face"])
print(f"Extracted embedding: type={type(embedding)}, length={len(embedding)}")

assert isinstance(embedding, list), "Embedding must be a list of floats"
assert len(embedding) == 128, f"Expected 128-dimensional embedding, got {len(embedding)}"
assert all(isinstance(x, float) for x in embedding), "All embedding elements must be floats"

# Ensure vector elements are non-trivial
zero_count = sum(1 for x in embedding if abs(x) < 1e-6)
assert zero_count < 10, "Embedding is mostly zeros, extraction failed"

print("All FacePipeline validation tests PASSED successfully!")

# 7. Clean up test image
try:
    if created_test_image and os.path.exists(TEST_IMAGE):
        os.remove(TEST_IMAGE)
        print("Test face image lena.jpg cleaned up successfully.")
except Exception as e:
    print(f"Warning: failed to delete test image: {e}")

sys.exit(0)
