import os
import subprocess
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.join(ROOT_DIR, "app")
sys.path.insert(0, APP_DIR)

from fastapi.testclient import TestClient  # noqa: E402

from database import SessionLocal  # noqa: E402
from main import app  # noqa: E402
import models  # noqa: E402


def run_seed() -> None:
    subprocess.run(
        [sys.executable, os.path.join(ROOT_DIR, "scripts", "setup_database.py"), "--seed-demo"],
        cwd=ROOT_DIR,
        check=True,
    )


def assert_demo_counts() -> None:
    db = SessionLocal()
    try:
        camera = db.query(models.Camera).filter_by(name="Demo Gate").one_or_none()
        assert camera is not None, "Demo Gate camera was not seeded."
        assert camera.config is not None, "Demo Gate camera config was not seeded."

        people = (
            db.query(models.Person)
            .filter(models.Person.member_code.in_(["DEMO-STUDENT-001", "DEMO-FACULTY-001"]))
            .all()
        )
        assert len(people) == 2, f"Expected 2 demo persons, got {len(people)}."

        person_ids = [person.id for person in people]
        templates = db.query(models.FaceTemplate).filter(models.FaceTemplate.person_id.in_(person_ids)).all()
        assert len(templates) == 2, f"Expected 2 demo face templates, got {len(templates)}."
        assert all(len(template.embedding_vector) == 128 for template in templates), "Demo embeddings must be 128-d."

        unknown = db.query(models.UnknownIdentity).filter_by(anonymous_code="UNKNOWN_DEMO_0001").one_or_none()
        assert unknown is not None, "Demo unknown identity was not seeded."

        events = db.query(models.Event).filter_by(camera_id=camera.id).all()
        demo_events = [
            event
            for event in events
            if event.track_id >= 9000 and event.track_id < 9010
        ]
        assert len(demo_events) == 6, f"Expected 6 demo events, got {len(demo_events)}."

        sessions = db.query(models.VisitSession).filter_by(entry_camera_id=camera.id).all()
        demo_sessions = [
            session
            for session in sessions
            if session.person_id in person_ids or session.unknown_id == unknown.id
        ]
        assert len(demo_sessions) == 4, f"Expected 4 demo sessions, got {len(demo_sessions)}."
        assert sum(1 for session in demo_sessions if session.status == "ACTIVE") == 2, "Expected 2 active demo sessions."
        assert sum(1 for session in demo_sessions if session.status == "CLOSED") == 2, "Expected 2 closed demo sessions."
    finally:
        db.close()


def assert_api_reads_demo_data() -> None:
    with TestClient(app) as client:
        sessions_response = client.get("/api/sessions")
        assert sessions_response.status_code == 200, sessions_response.text
        sessions = sessions_response.json()
        assert any(session["person_name"] == "Nguyen Minh Demo" for session in sessions), "Known demo session missing."
        assert any(session["person_name"] == "UNKNOWN_DEMO_0001" for session in sessions), "Unknown demo session missing."

        occupancy_response = client.get("/api/stats/occupancy")
        assert occupancy_response.status_code == 200, occupancy_response.text
        occupancy = occupancy_response.json()
        assert occupancy["current_occupancy"] >= 2, f"Expected occupancy >= 2, got {occupancy['current_occupancy']}."
        assert occupancy["known_visitors_today"] >= 2, "Expected known visitor entries in occupancy stats."
        assert occupancy["unknown_visitors_today"] >= 2, "Expected unknown visitor entries in occupancy stats."
        assert occupancy["total_sessions_today"] >= 4, "Expected seeded sessions in occupancy stats."

        hourly_response = client.get("/api/stats/hourly")
        assert hourly_response.status_code == 200, hourly_response.text
        hourly = hourly_response.json()
        assert len(hourly) == 24, f"Expected 24 hourly buckets, got {len(hourly)}."
        assert sum(bucket["entry"] for bucket in hourly) >= 4, "Expected seeded entry events in hourly stats."


def main() -> None:
    print("Running demo seed validation...")
    run_seed()
    assert_demo_counts()

    print("Running seed a second time to verify idempotency...")
    run_seed()
    assert_demo_counts()
    assert_api_reads_demo_data()

    print("Demo seed validation PASSED.")


if __name__ == "__main__":
    main()
