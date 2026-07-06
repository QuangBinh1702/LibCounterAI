import os
import sys
import datetime

# Setup paths
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models

print("Starting validation of backend CRUD and stats API endpoints...")

# 1. Helper to clear test records
def cleanup_data(member_code):
    db = SessionLocal()
    try:
        person = db.query(models.Person).filter_by(member_code=member_code).first()
        if person:
            # Delete templates and sessions/events
            db.query(models.FaceTemplate).filter_by(person_id=person.id).delete()
            db.query(models.VisitSession).filter_by(person_id=person.id).delete()
            db.query(models.Event).filter_by(person_id=person.id).delete()
            db.delete(person)
            db.commit()
            print(f"Cleaned up seeding data for member_code: {member_code}")
    except Exception as e:
        db.rollback()
        print(f"Cleanup error: {e}")
    finally:
        db.close()

cleanup_data("SV111222")

# 2. Seed data for testing
db = SessionLocal()
try:
    # 1. Camera
    camera = db.query(models.Camera).first()
    if not camera:
        camera = models.Camera(name="Test Camera", source_type="WEBCAM", source_url="0", status="ONLINE")
        db.add(camera)
        db.flush()
        
    # 2. Person
    person = models.Person(full_name="Nguyen Van B", member_code="SV111222", role="FACULTY", status="ACTIVE")
    db.add(person)
    db.flush()
    
    # 3. FaceTemplate
    template = models.FaceTemplate(
        person_id=person.id,
        embedding_vector=[0.1] * 128,
        model_name="sface",
        model_version="2021dec",
        quality_score=0.95,
        source_type="UPLOAD",
        is_active=True
    )
    db.add(template)
    
    # 4. Event
    event = models.Event(
        event_type="ENTRY",
        identity_type="KNOWN",
        person_id=person.id,
        track_id=42,
        camera_id=camera.id,
        confidence=0.95,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(event)
    db.flush()
    
    # 5. Session
    session = models.VisitSession(
        identity_type="KNOWN",
        person_id=person.id,
        entry_camera_id=camera.id,
        entry_event_id=event.id,
        entry_at=datetime.datetime.utcnow(),
        status="ACTIVE"
    )
    db.add(session)
    db.commit()
    print("Database seeding completed.")
except Exception as e:
    db.rollback()
    print(f"Seeding failed: {e}")
    sys.exit(1)
finally:
    db.close()

# 3. Test API endpoints
try:
    with TestClient(app) as client:
        # A. GET /api/persons
        print("\n--- Testing GET /api/persons ---")
        res_persons = client.get("/api/persons")
        assert res_persons.status_code == 200
        persons_list = res_persons.json()
        assert any(p["member_code"] == "SV111222" for p in persons_list)
        person_id = next(p["id"] for p in persons_list if p["member_code"] == "SV111222")
        print(f"Persons fetched successfully. Target Person ID: {person_id}")
        
        # B. GET /api/events
        print("\n--- Testing GET /api/events ---")
        res_events = client.get("/api/events")
        assert res_events.status_code == 200
        events_list = res_events.json()
        assert any(e["member_code"] == "SV111222" for e in events_list)
        print("Events fetched successfully.")
        
        # C. GET /api/sessions
        print("\n--- Testing GET /api/sessions ---")
        res_sessions = client.get("/api/sessions")
        assert res_sessions.status_code == 200
        sessions_list = res_sessions.json()
        assert any(s["member_code"] == "SV111222" for s in sessions_list)
        print("Sessions fetched successfully.")
        
        # D. GET /api/stats/occupancy
        print("\n--- Testing GET /api/stats/occupancy ---")
        res_occupancy = client.get("/api/stats/occupancy")
        assert res_occupancy.status_code == 200
        occ_data = res_occupancy.json()
        print(f"Occupancy Data: {occ_data}")
        assert occ_data["current_occupancy"] >= 1
        assert occ_data["total_entries_today"] >= 1
        
        # E. GET /api/stats/hourly
        print("\n--- Testing GET /api/stats/hourly ---")
        res_hourly = client.get("/api/stats/hourly")
        assert res_hourly.status_code == 200
        hourly_data = res_hourly.json()
        assert len(hourly_data) == 24
        print("Hourly stats fetched successfully.")
        
        # F. DELETE /api/persons/{id}
        print(f"\n--- Testing DELETE /api/persons/{person_id} ---")
        res_del = client.delete(f"/api/persons/{person_id}")
        assert res_del.status_code == 200
        print("Person deleted successfully.")
        
        # G. Re-verify Person is gone
        res_persons_after = client.get("/api/persons")
        persons_list_after = res_persons_after.json()
        assert not any(p["member_code"] == "SV111222" for p in persons_list_after)
        print("Verified: Person no longer exists in database.")
        
    print("\nAll REST API CRUD and stats endpoints validated successfully!")
    tests_passed = True
except Exception as e:
    print(f"\nAPI validation FAILED: {e}")
    tests_passed = False

cleanup_data("SV111222")

if tests_passed:
    sys.exit(0)
else:
    sys.exit(1)
