import os
import sys

# Setup paths
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models

print("Starting validation of Camera Management and Connection Testing APIs...")

# Helper to clean up
def cleanup_camera(name):
    db = SessionLocal()
    try:
        camera = db.query(models.Camera).filter_by(name=name).first()
        if camera:
            db.delete(camera)
            db.commit()
            print(f"Cleaned up camera: {name}")
    except Exception as e:
        db.rollback()
        print(f"Cleanup error: {e}")
    finally:
        db.close()

cleanup_camera("RTSP Test Camera")

try:
    with TestClient(app) as client:
        # A. Attempt registration with INVALID RTSP URL
        print("\n--- A. Registering camera with invalid RTSP ---")
        res_invalid = client.post(
            "/api/cameras",
            json={
                "name": "RTSP Test Camera",
                "source_type": "RTSP",
                "source_url": "rtsp://invalid_address:8554/live"
            }
        )
        print(f"Response status: {res_invalid.status_code}")
        print(f"Response body: {res_invalid.json()}")
        assert res_invalid.status_code == 400
        assert "Failed to connect" in res_invalid.json()["detail"]
        
        # B. Register camera with mock file (invalid path first)
        print("\n--- B. Registering camera with invalid FILE path ---")
        res_file_invalid = client.post(
            "/api/cameras",
            json={
                "name": "RTSP Test Camera",
                "source_type": "FILE",
                "source_url": "invalid_video_file.mp4"
            }
        )
        assert res_file_invalid.status_code == 400
        assert "Video file does not exist" in res_file_invalid.json()["detail"]
        
        # C. Register a WEBCAM stream (with index -1 to mock failure/success)
        print("\n--- C. Registering camera with WEBCAM index ---")
        res_webcam = client.post(
            "/api/cameras",
            json={
                "name": "RTSP Test Camera",
                "source_type": "WEBCAM",
                "source_url": "-1" # Invalid camera index is safe to register, defaults to OFFLINE
            }
        )
        assert res_webcam.status_code == 200
        cam_data = res_webcam.json()
        assert cam_data["name"] == "RTSP Test Camera"
        cam_id = cam_data["id"]
        print(f"Registered camera index successfully. Camera ID: {cam_id}")
        
        # D. Test Connection API
        print(f"\n--- D. Testing camera connection (ID: {cam_id}) ---")
        res_test = client.post(f"/api/cameras/{cam_id}/test")
        assert res_test.status_code == 200
        print(f"Test connection result: {res_test.json()}")
        assert "status" in res_test.json()
        
    print("\nAll camera registration and connection validation tests PASSED!")
    tests_passed = True
except Exception as e:
    print(f"\nCamera API validation FAILED: {e}")
    tests_passed = False

cleanup_camera("RTSP Test Camera")

if tests_passed:
    sys.exit(0)
else:
    sys.exit(1)
