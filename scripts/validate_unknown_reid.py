import os
import sys
import cv2
import json
import datetime
import urllib.request

# Setup paths
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models

TEST_IMAGE = os.path.join(CWD, "lena_matching.jpg")

print("Starting Unknown Visitor Re-identification and Session validation tests...")

# 1. Download test face image if not present
if not os.path.exists(TEST_IMAGE):
    print("Downloading test face image...")
    try:
        urllib.request.urlretrieve('https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg', TEST_IMAGE)
    except Exception as e:
        print(f"Failed to download test face image: {e}")
        sys.exit(1)

# 2. Cleanup function
def cleanup_database():
    db = SessionLocal()
    try:
        # Delete all unknown identities, events, and sessions to get a clean testing state
        db.query(models.VisitSession).delete()
        db.query(models.Event).delete()
        db.query(models.UnknownIdentity).delete()
        # Also ensure no KNOWN person exists for test
        person = db.query(models.Person).filter_by(member_code="SV777777").first()
        if person:
            db.delete(person)
        db.commit()
        print("Database cleaned up successfully.")
    except Exception as e:
        print(f"Database cleanup failed: {e}")
        db.rollback()
    finally:
        db.close()

cleanup_database()

# 3. Run tests with TestClient
try:
    with TestClient(app) as client:
        # A. Process Frame 1: Person detected (no KNOWN registered).
        # Should create a new UnknownIdentity and return it.
        print("\n--- A. Processing Frame 1 (First Encounter - New Unknown) ---")
        mock_dets = [[0, 0, 512, 400, 0.95]]
        
        with open(TEST_IMAGE, "rb") as f:
            response_frame1 = client.post(
                "/api/process-frame",
                data={
                    "session_id": "session_unk_test_1",
                    "mock_detections": json.dumps(mock_dets),
                    "line_config": json.dumps([[0, 450], [512, 450]]) # Virtual line at y=450
                },
                files={"file": ("frame1.jpg", f, "image/jpeg")}
            )
            
        assert response_frame1.status_code == 200, f"Frame 1 failed: {response_frame1.json()}"
        res1 = response_frame1.json()
        print(f"Frame 1 response: {res1}")
        
        assert len(res1["tracks"]) == 1, "Expected 1 track"
        t1 = res1["tracks"][0]
        assert t1["identity_type"] == "UNKNOWN", f"Expected UNKNOWN, got {t1['identity_type']}"
        anon_code = t1["person_name"]
        assert anon_code.startswith("UNKNOWN_"), f"Expected UNKNOWN_ format, got {anon_code}"
        print(f"Successfully generated new anonymous code: {anon_code}")
        
        # Verify in DB
        db = SessionLocal()
        unk_in_db = db.query(models.UnknownIdentity).filter_by(anonymous_code=anon_code).first()
        assert unk_in_db is not None, "UnknownIdentity not found in DB"
        assert unk_in_db.visit_count == 1, f"Expected visit_count 1, got {unk_in_db.visit_count}"
        db.close()
        
        # B. Process Frame 2: Same face (with a new session/track to simulate another visitor with same face).
        # Should match the existing UnknownIdentity (Re-identification).
        print("\n--- B. Processing Frame 2 (Second Encounter - Re-ID) ---")
        with open(TEST_IMAGE, "rb") as f:
            response_frame2 = client.post(
                "/api/process-frame",
                data={
                    "session_id": "session_unk_test_2",
                    "mock_detections": json.dumps(mock_dets),
                    "line_config": json.dumps([[0, 450], [512, 450]])
                },
                files={"file": ("frame2.jpg", f, "image/jpeg")}
            )
            
        assert response_frame2.status_code == 200, f"Frame 2 failed: {response_frame2.json()}"
        res2 = response_frame2.json()
        print(f"Frame 2 response: {res2}")
        
        assert len(res2["tracks"]) == 1, "Expected 1 track"
        t2 = res2["tracks"][0]
        assert t2["identity_type"] == "UNKNOWN", f"Expected UNKNOWN, got {t2['identity_type']}"
        assert t2["person_name"] == anon_code, f"Expected same anonymous code {anon_code}, got {t2['person_name']}"
        print("Re-identification successful!")
        
        # Verify visit_count incremented in DB
        db = SessionLocal()
        unk_in_db = db.query(models.UnknownIdentity).filter_by(anonymous_code=anon_code).first()
        assert unk_in_db.visit_count == 2, f"Expected visit_count 2, got {unk_in_db.visit_count}"
        db.close()

        # C. Process Frame 3: Crosses line (ENTRY).
        # Bbox bottom center goes below 450.
        print("\n--- C. Processing Frame 3 (ENTRY Crossing Event) ---")
        mock_dets_entry = [[0, 0, 512, 480, 0.95]] # y2=480, crosses y=450
        with open(TEST_IMAGE, "rb") as f:
            response_frame3 = client.post(
                "/api/process-frame",
                data={
                    "session_id": "session_unk_test_2",
                    "mock_detections": json.dumps(mock_dets_entry),
                    "line_config": json.dumps([[0, 450], [512, 450]])
                },
                files={"file": ("frame3.jpg", f, "image/jpeg")}
            )
            
        assert response_frame3.status_code == 200, f"Frame 3 failed: {response_frame3.json()}"
        res3 = response_frame3.json()
        print(f"Frame 3 response: {res3}")
        
        # Verify Event and Active VisitSession created
        db = SessionLocal()
        event_entry = db.query(models.Event).filter_by(event_type="ENTRY").first()
        assert event_entry is not None, "ENTRY event not found in DB"
        assert event_entry.identity_type == "UNKNOWN", "Event identity should be UNKNOWN"
        
        sess_active = db.query(models.VisitSession).filter_by(status="ACTIVE").first()
        assert sess_active is not None, "Active VisitSession not found in DB"
        assert sess_active.identity_type == "UNKNOWN", "VisitSession identity should be UNKNOWN"
        assert sess_active.unknown_identity.anonymous_code == anon_code, "VisitSession not linked to correct unknown visitor"
        print("ENTRY event and Active VisitSession logged successfully.")
        db.close()

        # D. Process Frame 4: Crosses line (EXIT).
        # We need a new session or reset track trajectory so it triggers EXIT.
        # Let's register a track starting below the line and moving above it.
        # Frame 4a: track starts at y=480 (below line)
        print("\n--- D. Processing Frame 4a (EXIT trajectories - below line) ---")
        mock_dets_exit_start = [[0, 0, 512, 480, 0.95]]
        with open(TEST_IMAGE, "rb") as f:
            client.post(
                "/api/process-frame",
                data={
                    "session_id": "session_unk_test_exit",
                    "mock_detections": json.dumps(mock_dets_exit_start),
                    "line_config": json.dumps([[0, 450], [512, 450]])
                },
                files={"file": ("frame4a.jpg", f, "image/jpeg")}
            )
        
        # Frame 4b: track moves to y=400 (above line)
        print("\n--- D. Processing Frame 4b (EXIT trajectories - above line) ---")
        mock_dets_exit_end = [[0, 0, 512, 400, 0.95]]
        with open(TEST_IMAGE, "rb") as f:
            response_exit = client.post(
                "/api/process-frame",
                data={
                    "session_id": "session_unk_test_exit",
                    "mock_detections": json.dumps(mock_dets_exit_end),
                    "line_config": json.dumps([[0, 450], [512, 450]])
                },
                files={"file": ("frame4b.jpg", f, "image/jpeg")}
            )
            
        assert response_exit.status_code == 200, f"Exit frame failed: {response_exit.json()}"
        print(f"Exit response: {response_exit.json()}")
        
        # Verify Session is now CLOSED
        db = SessionLocal()
        sess_closed = db.query(models.VisitSession).filter_by(status="CLOSED").first()
        assert sess_closed is not None, "Closed VisitSession not found in DB"
        assert sess_closed.exit_at is not None, "exit_at not filled"
        assert sess_closed.duration_seconds is not None, "duration_seconds not calculated"
        print(f"VisitSession CLOSED successfully. Duration: {sess_closed.duration_seconds}s")
        db.close()
        
        # E. Query API endpoints
        print("\n--- E. Verifying API endpoints ---")
        sessions_res = client.get("/api/sessions")
        assert sessions_res.status_code == 200, "Failed to call /api/sessions"
        sess_list = sessions_res.json()
        print(f"Sessions API response: {sess_list}")
        assert len(sess_list) > 0, "No sessions returned"
        assert sess_list[0]["person_name"] == anon_code, f"Expected {anon_code}, got {sess_list[0]['person_name']}"
        
        events_res = client.get("/api/events")
        assert events_res.status_code == 200, "Failed to call /api/events"
        events_list = events_res.json()
        print(f"Events API response: {events_list}")
        assert len(events_list) > 0, "No events returned"

        print("\nAll Unknown Visitor Re-identification and Session validation tests PASSED!")

except Exception as e:
    print(f"Test failed with exception: {e}")
    sys.exit(1)
finally:
    cleanup_database()
