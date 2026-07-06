import os
import sys
import cv2
import numpy as np
import urllib.request

# Setup paths
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models

TEST_IMAGE = os.path.join(CWD, "lena_enrollment.jpg")
BLANK_IMAGE = os.path.join(CWD, "blank_no_face.jpg")

print("Starting enrollment validation tests...")

# 1. Download test face image if not present
if not os.path.exists(TEST_IMAGE):
    print("Downloading test face image...")
    try:
        urllib.request.urlretrieve('https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg', TEST_IMAGE)
    except Exception as e:
        print(f"Failed to download test face image: {e}")
        sys.exit(1)

# 2. Create a blank image with no faces
img_blank = np.ones((400, 400, 3), dtype=np.uint8) * 128
cv2.imwrite(BLANK_IMAGE, img_blank)

# 3. Define helper for test cleanup
def cleanup_database(member_code):
    db = SessionLocal()
    try:
        person = db.query(models.Person).filter_by(member_code=member_code).first()
        if person:
            print(f"Cleaning up database records for member_code: {member_code}")
            db.delete(person)
            db.commit()
    except Exception as e:
        print(f"Database cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

# Cleanup database first to ensure clean state
cleanup_database("SV999999")
cleanup_database("SV888888")

# 4. Run tests with TestClient
try:
    with TestClient(app) as client:
        # A. Test Successful Registration
        print("\n--- Testing Successful Registration ---")
        with open(TEST_IMAGE, "rb") as f:
            response = client.post(
                "/api/persons/register",
                data={
                    "full_name": "Nguyen Van A",
                    "member_code": "SV999999",
                    "role": "STUDENT",
                    "status": "ACTIVE"
                },
                files={"file": ("lena.jpg", f, "image/jpeg")}
            )
            
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        assert response.status_code == 201, "Expected status code 201"
        data = response.json()
        assert data["full_name"] == "Nguyen Van A"
        assert data["member_code"] == "SV999999"
        assert "face_template" in data
        assert data["face_template"]["model_name"] == "sface"
        
        # Verify in Database
        db = SessionLocal()
        db_person = db.query(models.Person).filter_by(member_code="SV999999").first()
        assert db_person is not None, "Person record was not found in DB"
        assert len(db_person.face_templates) == 1, "Expected 1 FaceTemplate linked to Person"
        
        # Verify vector shape
        vector = db_person.face_templates[0].embedding_vector
        assert len(vector) == 128, f"Expected 128-dimensional embedding, got {len(vector)}"
        db.close()
        
        # B. Test Duplicate member_code Registration
        print("\n--- Testing Duplicate Registration ---")
        with open(TEST_IMAGE, "rb") as f:
            response_dup = client.post(
                "/api/persons/register",
                data={
                    "full_name": "Nguyen Van B",
                    "member_code": "SV999999",
                    "role": "STUDENT",
                    "status": "ACTIVE"
                },
                files={"file": ("lena.jpg", f, "image/jpeg")}
            )
            
        print(f"Status code: {response_dup.status_code}")
        print(f"Response: {response_dup.json()}")
        assert response_dup.status_code == 400, "Expected status 400 for duplicate member code"
        assert "already registered" in response_dup.json()["detail"]

        # C. Test Registration with No Face
        print("\n--- Testing Registration with No Face ---")
        with open(BLANK_IMAGE, "rb") as f:
            response_noface = client.post(
                "/api/persons/register",
                data={
                    "full_name": "Nguyen Van C",
                    "member_code": "SV888888",
                    "role": "STUDENT",
                    "status": "ACTIVE"
                },
                files={"file": ("blank.jpg", f, "image/jpeg")}
            )
            
        print(f"Status code: {response_noface.status_code}")
        print(f"Response: {response_noface.json()}")
        assert response_noface.status_code == 400, "Expected status 400 for no face image"
        assert "No face detected" in response_noface.json()["detail"]

    print("\nAll enrollment validation tests PASSED successfully!")
    tests_passed = True
except Exception as e:
    print(f"\nEnrollment validation FAILED: {e}")
    tests_passed = False

# 5. Clean up files and DB
if os.path.exists(TEST_IMAGE):
    os.remove(TEST_IMAGE)
if os.path.exists(BLANK_IMAGE):
    os.remove(BLANK_IMAGE)

cleanup_database("SV999999")
cleanup_database("SV888888")

if tests_passed:
    sys.exit(0)
else:
    sys.exit(1)
