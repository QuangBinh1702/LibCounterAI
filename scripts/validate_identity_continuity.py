import datetime
import io
import json
import os
import sys

import cv2
import numpy as np

CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from fastapi.testclient import TestClient  # noqa: E402
from database import engine, SessionLocal  # noqa: E402
from main import app  # noqa: E402
import models  # noqa: E402

TEST_MEMBER_CODE = "SV_CONTINUITY"


def make_blank_frame() -> bytes:
    img = np.full((480, 640, 3), 245, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", img)
    if not ok:
        raise RuntimeError("Could not encode validation frame")
    return encoded.tobytes()


def cleanup_database() -> None:
    db = SessionLocal()
    try:
        db.query(models.VisitSession).delete()
        db.query(models.Event).delete()
        person = db.query(models.Person).filter_by(member_code=TEST_MEMBER_CODE).first()
        if person:
            db.delete(person)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_active_known_session() -> int:
    db = SessionLocal()
    try:
        camera = models.Camera(
            name="Continuity Test Camera",
            source_type="WEBCAM",
            source_url="0",
            status="ONLINE",
        )
        person = models.Person(
            full_name="Nguyen Continuity",
            member_code=TEST_MEMBER_CODE,
            role="STUDENT",
            status="ACTIVE",
        )
        db.add(camera)
        db.add(person)
        db.flush()

        entry_event = models.Event(
            event_type="ENTRY",
            identity_type="KNOWN",
            person_id=person.id,
            track_id=9001,
            camera_id=camera.id,
            confidence=0.95,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            metadata_json={"resolution": "seed"},
        )
        db.add(entry_event)
        db.flush()

        session = models.VisitSession(
            identity_type="KNOWN",
            person_id=person.id,
            entry_camera_id=camera.id,
            entry_event_id=entry_event.id,
            entry_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10),
            status="ACTIVE",
        )
        db.add(session)
        db.commit()
        return person.id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def post_frame(client: TestClient, detections: list[list[float]]) -> dict:
    response = client.post(
        "/api/process-frame",
        data={
            "session_id": "identity_continuity_exit",
            "line_config": json.dumps([[0, 450], [512, 450]]),
            "mock_detections": json.dumps(detections),
            "fast_mode": "true",
            "identity_probe": "false",
            "detect_frame": "true",
        },
        files={"file": ("frame.jpg", io.BytesIO(make_blank_frame()), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def main() -> int:
    print("Starting identity continuity validation...")
    models.Base.metadata.create_all(bind=engine)
    cleanup_database()
    person_id = seed_active_known_session()

    try:
        with TestClient(app) as client:
            first = post_frame(client, [[0, 0, 120, 480, 0.95]])
            second = post_frame(client, [[0, 0, 120, 400, 0.95]])

        assert first["crossing_events"] == [], first
        events = second.get("crossing_events", [])
        assert len(events) == 1, second
        event = events[0]
        assert event["direction"] == "EXIT", second
        assert event["identity_type"] == "KNOWN", second
        assert event["person_name"] == "Nguyen Continuity", second
        assert event["identity_resolution"] == "session_continuity", second

        db = SessionLocal()
        try:
            session = db.query(models.VisitSession).filter_by(person_id=person_id).one()
            assert session.status == "CLOSED", f"Expected CLOSED, got {session.status}"
            assert session.exit_at is not None, "Expected exit_at"
            exit_event = db.query(models.Event).filter_by(event_type="EXIT").one()
            assert exit_event.identity_type == "KNOWN", "Expected inferred KNOWN exit event"
            assert exit_event.metadata_json["resolution"] == "session_continuity"
        finally:
            db.close()

        print("Identity continuity validation PASSED.")
        return 0
    finally:
        cleanup_database()


if __name__ == "__main__":
    raise SystemExit(main())
