import os
import sys
import cv2
import json
import urllib.request

# Setup paths
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models

TEST_IMAGE = os.path.join(CWD, "lena_matching.jpg")

print("Starting face matching and identification validation tests...")

# 1. Download test face image if not present
if not os.path.exists(TEST_IMAGE):
    print("Downloading test face image...")
    try:
        urllib.request.urlretrieve('https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg', TEST_IMAGE)
    except Exception as e:
        print(f"Failed to download test face image: {e}")
        sys.exit(1)

# 2. Define helper for test cleanup
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
cleanup_database("SV777777")

# 3. Run tests with TestClient
try:
    with TestClient(app) as client:
        # A. Register Nguyen Van A (SV777777)
        print("\n--- A. Enrolling Test Person ---")
        with open(TEST_IMAGE, "rb") as f:
            response = client.post(
                "/api/persons/register",
                data={
                    "full_name": "Nguyen Van A",
                    "member_code": "SV777777",
                    "role": "STUDENT",
                    "status": "ACTIVE"
                },
                files={"file": ("lena.jpg", f, "image/jpeg")}
            )
        assert response.status_code == 201, f"Enrollment failed: {response.json()}"
        print("Test person enrolled successfully.")
        
        # B. Process Frame 1: Person detected, triggers face matching
        print("\n--- B. Processing Frame 1 (Face Detection and Matching) ---")
        # Mock detection coordinates: [x1, y1, x2, y2, confidence]
        # Bbox covers the image down to y=400, bottom center is at (256, 400) - above line at 450
        mock_dets = [[0, 0, 512, 400, 0.95]]
        
        with open(TEST_IMAGE, "rb") as f:
            response_frame1 = client.post(
                "/api/process-frame",
                data={
                    "session_id": "session_match_test",
                    "mock_detections": json.dumps(mock_dets),
                    "line_config": json.dumps([[0, 450], [512, 450]]) # Virtual line at y=450
                },
                files={"file": ("frame1.jpg", f, "image/jpeg")}
            )
            
        print(f"Frame 1 status: {response_frame1.status_code}")
        res_data1 = response_frame1.json()
        print(f"Frame 1 response: {res_data1}")
        
        assert response_frame1.status_code == 200, "Expected status 200"
        assert len(res_data1["tracks"]) == 1, "Expected 1 active track"
        track = res_data1["tracks"][0]
        assert track["identity_type"] == "KNOWN", f"Expected identity KNOWN, got {track['identity_type']}"
        assert track["person_name"] == "Nguyen Van A", f"Expected person name Nguyen Van A, got {track['person_name']}"
        
        # C. Process Frame 2: Bbox shifts, triggers line crossing and logs event/session
        print("\n--- C. Processing Frame 2 (Line Crossing Event Log) ---")
        # Bbox shifts downwards to y=480, bottom center becomes (256, 480) - crosses line at y=450
        mock_dets_2 = [[0, 0, 512, 480, 0.95]]
        
        with open(TEST_IMAGE, "rb") as f:
            response_frame2 = client.post(
                "/api/process-frame",
                data={
                    "session_id": "session_match_test",
                    "mock_detections": json.dumps(mock_dets_2),
                    "line_config": json.dumps([[0, 450], [512, 450]])
                },
                files={"file": ("frame2.jpg", f, "image/jpeg")}
            )
            
        print(f"Frame 2 status: {response_frame2.status_code}")
        res_data2 = response_frame2.json()
        print(f"Frame 2 response: {res_data2}")
        
        assert response_frame2.status_code == 200, "Expected status 200"
        assert len(res_data2["crossing_events"]) == 1, "Expected 1 crossing event"
        event = res_data2["crossing_events"][0]
        assert event["direction"] == "ENTRY", f"Expected direction ENTRY, got {event['direction']}"
        
        # D. Verify DB Records
        print("\n--- D. Verifying Database Event Logging ---")
        db = SessionLocal()
        db_person = db.query(models.Person).filter_by(member_code="SV777777").first()
        
        # Check Event record
        db_event = db.query(models.Event).filter_by(person_id=db_person.id).first()
        assert db_event is not None, "Event was not logged to the database"
        assert db_event.event_type == "ENTRY", f"Expected event type ENTRY, got {db_event.event_type}"
        assert db_event.identity_type == "KNOWN", "Expected event identity type KNOWN"
        print("Verified: Event logged successfully in database.")
        
        # Check VisitSession record
        db_session = db.query(models.VisitSession).filter_by(person_id=db_person.id).first()
        assert db_session is not None, "VisitSession was not logged to the database"
        assert db_session.status == "ACTIVE", f"Expected session status ACTIVE, got {db_session.status}"
        print("Verified: VisitSession initialized successfully in database.")
        
        # E. Process Frame 3: Simulate EXIT direction
        print("\n--- E. Processing Frame 3 (Simulate EXIT and Close Session) ---")
        # Prev: bottom center is (256, 480)
        # Curr: bottom center is (256, 400) - crosses back to outside (EXIT)
        mock_dets_3 = [[0, 0, 512, 400, 0.95]]
        
        with open(TEST_IMAGE, "rb") as f:
            response_frame3 = client.post(
                "/api/process-frame",
                data={
                    "session_id": "session_match_test",
                    "mock_detections": json.dumps(mock_dets_3),
                    "line_config": json.dumps([[0, 450], [512, 450]])
                },
                files={"file": ("frame3.jpg", f, "image/jpeg")}
            )
            
        print(f"Frame 3 status: {response_frame3.status_code}")
        res_data3 = response_frame3.json()
        print(f"Frame 3 response: {res_data3}")
        
        assert len(res_data3["crossing_events"]) == 1, "Expected 1 crossing event"
        assert res_data3["crossing_events"][0]["direction"] == "EXIT", "Expected direction EXIT"
        
        # Re-query session status to see if it is CLOSED
        db.refresh(db_session)
        assert db_session.status == "CLOSED", f"Expected closed session, got {db_session.status}"
        assert db_session.duration_seconds is not None, "Expected duration_seconds to be computed"
        print(f"Verified: VisitSession closed successfully in database (duration={db_session.duration_seconds}s).")
        
        db.close()
        
    print("\nAll face matching and identification validation tests PASSED successfully!")
    tests_passed = True
except Exception as e:
    print(f"\nMatching validation FAILED: {e}")
    import traceback
    traceback.print_exc()
    tests_passed = False

# 4. Clean up files and DB
if os.path.exists(TEST_IMAGE):
    os.remove(TEST_IMAGE)

cleanup_database("SV777777")

if tests_passed:
    sys.exit(0)
else:
    sys.exit(1)
