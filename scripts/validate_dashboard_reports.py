import os
import sys
import json

# Setup paths
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models
import datetime

print("Starting E04 Dashboard & Reports validation tests...")

# 1. Cleanup
def cleanup():
    db = SessionLocal()
    try:
        db.query(models.VisitSession).delete()
        db.query(models.Event).delete()
        db.query(models.UnknownIdentity).delete()
        db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

cleanup()

# 2. Seed test data directly
db = SessionLocal()
now = datetime.datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0)

# Create a camera
cam = models.Camera(name="Test Cam", source_type="WEBCAM", source_url="0", status="ONLINE")
db.add(cam)
db.flush()

# Create an unknown identity
unk = models.UnknownIdentity(
    anonymous_code="UNKNOWN_20260706_0001",
    embedding_vector=[0.1] * 128,
    expire_at=now + datetime.timedelta(hours=24),
    status="ACTIVE"
)
db.add(unk)
db.flush()

# Create ENTRY event for unknown
entry_evt = models.Event(
    event_type="ENTRY", identity_type="UNKNOWN",
    unknown_id=unk.id, track_id=1, camera_id=cam.id,
    confidence=0.85, timestamp=now - datetime.timedelta(hours=2)
)
db.add(entry_evt)
db.flush()

# Create EXIT event for unknown
exit_evt = models.Event(
    event_type="EXIT", identity_type="UNKNOWN",
    unknown_id=unk.id, track_id=1, camera_id=cam.id,
    confidence=0.85, timestamp=now - datetime.timedelta(hours=1)
)
db.add(exit_evt)
db.flush()

# Create a closed session for unknown
sess = models.VisitSession(
    identity_type="UNKNOWN", unknown_id=unk.id,
    entry_camera_id=cam.id, entry_event_id=entry_evt.id,
    exit_camera_id=cam.id, exit_event_id=exit_evt.id,
    entry_at=now - datetime.timedelta(hours=2),
    exit_at=now - datetime.timedelta(hours=1),
    duration_seconds=3600, status="CLOSED"
)
db.add(sess)

# Create an active session for unknown (simulates someone still inside)
entry_evt2 = models.Event(
    event_type="ENTRY", identity_type="UNKNOWN",
    unknown_id=unk.id, track_id=2, camera_id=cam.id,
    confidence=0.90, timestamp=now - datetime.timedelta(minutes=30)
)
db.add(entry_evt2)
db.flush()

sess2 = models.VisitSession(
    identity_type="UNKNOWN", unknown_id=unk.id,
    entry_camera_id=cam.id, entry_event_id=entry_evt2.id,
    entry_at=now - datetime.timedelta(minutes=30),
    status="ACTIVE"
)
db.add(sess2)
db.commit()
db.close()

print("Test data seeded successfully.")

# 3. Run tests
try:
    with TestClient(app) as client:
        # A. Test occupancy API with known/unknown breakdown
        print("\n--- A. Testing /api/stats/occupancy ---")
        res = client.get("/api/stats/occupancy")
        assert res.status_code == 200
        data = res.json()
        print(f"Occupancy response: {data}")
        
        assert "known_visitors_today" in data, "Missing known_visitors_today"
        assert "unknown_visitors_today" in data, "Missing unknown_visitors_today"
        assert "total_sessions_today" in data, "Missing total_sessions_today"
        assert data["current_occupancy"] >= 1, f"Expected occupancy >= 1, got {data['current_occupancy']}"
        assert data["unknown_visitors_today"] >= 1, f"Expected unknown_visitors >= 1"
        assert data["total_sessions_today"] >= 2, f"Expected total_sessions >= 2, got {data['total_sessions_today']}"
        print("Occupancy API with breakdown PASSED!")
        
        # B. Test sessions API without date filter
        print("\n--- B. Testing /api/sessions (no filter) ---")
        res = client.get("/api/sessions")
        assert res.status_code == 200
        sessions = res.json()
        print(f"Sessions count: {len(sessions)}")
        assert len(sessions) >= 2, f"Expected >= 2 sessions, got {len(sessions)}"
        assert sessions[0].get("identity_type") is not None, "Missing identity_type field"
        print("Sessions API (no filter) PASSED!")
        
        # C. Test sessions API with date filter
        print("\n--- C. Testing /api/sessions?date=... ---")
        today = now.strftime("%Y-%m-%d")
        res = client.get(f"/api/sessions?date={today}")
        assert res.status_code == 200
        filtered = res.json()
        print(f"Filtered sessions for {today}: {len(filtered)}")
        assert len(filtered) >= 2, f"Expected >= 2 sessions for today"
        
        # Test with a past date that should have no sessions
        res2 = client.get("/api/sessions?date=2020-01-01")
        assert res2.status_code == 200
        assert len(res2.json()) == 0, "Expected 0 sessions for 2020-01-01"
        print("Sessions date filter PASSED!")
        
        # D. Test hourly stats
        print("\n--- D. Testing /api/stats/hourly ---")
        res = client.get("/api/stats/hourly")
        assert res.status_code == 200
        hourly = res.json()
        assert len(hourly) == 24, f"Expected 24 hours, got {len(hourly)}"
        total_entries = sum(h["entry"] for h in hourly)
        assert total_entries >= 2, f"Expected >= 2 entries in hourly, got {total_entries}"
        print("Hourly stats PASSED!")
        
        print("\nAll E04 Dashboard & Reports validation tests PASSED!")

except Exception as e:
    print(f"Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    cleanup()
