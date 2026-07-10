import io
import json
import os
import sys

import cv2
import numpy as np
from validation_assets import ensure_test_face

CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from fastapi.testclient import TestClient  # noqa: E402
from database import engine, SessionLocal  # noqa: E402
from main import app  # noqa: E402
import models  # noqa: E402

TEST_IMAGE = os.path.join(CWD, "lena_fast_mode.jpg")
TEST_MEMBER_CODE = "SV_FAST_MODE"


def make_frame() -> bytes:
    img = np.full((480, 640, 3), 245, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", img)
    if not ok:
        raise RuntimeError("Could not encode validation frame")
    return encoded.tobytes()


def cleanup_database() -> None:
    db = SessionLocal()
    try:
        people = db.query(models.Person).filter(
            (models.Person.member_code == TEST_MEMBER_CODE)
            | (models.Person.full_name == "Nguyen Fast Mode")
        ).all()
        for person in people:
            db.delete(person)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def post_frame(
    client: TestClient,
    session_id: str,
    detections: list[list[float]] | None,
    *,
    frame: bytes | None = None,
    line_config: list[list[int]] | None = None,
    identity_probe: bool = False,
    detect_frame: bool = True,
) -> dict:
    frame = frame or make_frame()
    data = {
        "session_id": session_id,
        "line_config": json.dumps(line_config or [[100, 280], [200, 280]]),
        "fast_mode": "true",
        "identity_probe": "true" if identity_probe else "false",
        "detect_frame": "true" if detect_frame else "false",
    }
    if detections is not None:
        data["mock_detections"] = json.dumps(detections)

    response = client.post(
        "/api/process-frame",
        data=data,
        files={"file": ("frame.jpg", io.BytesIO(frame), "image/jpeg")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def main() -> int:
    print("Starting realtime fast mode validation...")
    models.Base.metadata.create_all(bind=engine)
    cleanup_database()

    session_id = "fast_mode_validation"
    try:
        ensure_test_face(TEST_IMAGE)
        with TestClient(app) as client:
            with open(TEST_IMAGE, "rb") as f:
                register = client.post(
                    "/api/persons/register",
                    data={
                        "full_name": "Nguyen Fast Mode",
                        "member_code": TEST_MEMBER_CODE,
                        "role": "STUDENT",
                        "status": "ACTIVE",
                    },
                    files={"file": ("lena.jpg", f, "image/jpeg")},
                )
            assert register.status_code == 201, register.text

            with open(TEST_IMAGE, "rb") as f:
                face_frame = f.read()

            identity = post_frame(
                client,
                "fast_mode_identity_probe",
                [[0, 0, 512, 400, 0.95]],
                frame=face_frame,
                line_config=[[0, 450], [512, 450]],
                identity_probe=True,
            )
            assert identity["fast_mode"] is True
            assert identity["identity_probe"] is True
            assert identity["tracks"][0]["identity_type"] == "KNOWN", identity
            assert identity["tracks"][0]["person_name"] == "Nguyen Fast Mode", identity

            first = post_frame(client, session_id, [[100, 50, 200, 250, 0.9]])
            second = post_frame(client, session_id, [[100, 110, 200, 310, 0.9]])
            prediction_first = post_frame(
                client,
                "fast_mode_prediction",
                [[180, 100, 340, 420, 0.9]],
                line_config=[[320, 0], [320, 480]],
            )
            prediction_second = post_frame(
                client,
                "fast_mode_prediction",
                None,
                line_config=[[320, 0], [320, 480]],
                detect_frame=False,
            )

        assert first["fast_mode"] is True
        assert "processing_ms" in first
        assert len(first.get("crossing_events", [])) == 0

        events = second.get("crossing_events", [])
        assert len(events) == 1, second
        assert events[0]["direction"] == "ENTRY", second
        assert events[0]["identity_type"] == "UNKNOWN", second
        assert "processing_ms" in second
        assert prediction_first["detector_ran"] is True
        assert prediction_second["detector_ran"] is False
        assert prediction_second["detect_frame"] is False
        assert prediction_second["tracks"], prediction_second
        assert prediction_second["tracks"][0]["predicted"] is True, prediction_second

        print(
            "Realtime fast mode validation PASSED "
            f"(identity={identity['processing_ms']}ms, frame1={first['processing_ms']}ms, frame2={second['processing_ms']}ms)."
        )
        return 0
    finally:
        cleanup_database()
        if os.path.exists(TEST_IMAGE):
            os.remove(TEST_IMAGE)


if __name__ == "__main__":
    raise SystemExit(main())
