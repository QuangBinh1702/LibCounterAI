import datetime
import json
from unittest.mock import patch

import pytest
import numpy as np


def test_user_model_column_defaults():
    import models
    col = models.User.__table__.columns["status"]
    assert col.default is not None
    col = models.User.__table__.columns["role"]
    assert col.default is not None


def test_person_model_column_defaults():
    import models
    col = models.Person.__table__.columns["status"]
    assert col.default is not None


def test_face_template_column_defaults():
    import models
    assert models.FaceTemplate.__table__.columns["model_name"].default is not None
    assert models.FaceTemplate.__table__.columns["source_type"].default is not None
    assert models.FaceTemplate.__table__.columns["quality_score"].default is not None
    assert models.FaceTemplate.__table__.columns["is_active"].default is not None


def test_unknown_identity_column_defaults():
    import models
    col = models.UnknownIdentity.__table__.columns["status"]
    assert col.default is not None
    col = models.UnknownIdentity.__table__.columns["visit_count"]
    assert col.default is not None


def test_camera_model():
    import models
    cam = models.Camera(name="Test Cam", source_type="WEBCAM", source_url="0")
    assert cam.name == "Test Cam"
    assert cam.source_type == "WEBCAM"
    assert cam.source_url == "0"
    assert cam.status is None


def test_camera_config_column_defaults():
    import models
    assert models.CameraConfig.__table__.columns["debounce_seconds"].default is not None
    assert models.CameraConfig.__table__.columns["recognition_threshold"].default is not None
    assert models.CameraConfig.__table__.columns["unknown_threshold"].default is not None


def test_camera_config_required_fields():
    import models
    config = models.CameraConfig(
        camera_id=1,
        entry_line_config=[[0, 0], [100, 100]],
        exit_line_config=[[0, 100], [100, 0]],
    )
    assert config.camera_id == 1
    assert config.entry_line_config == [[0, 0], [100, 100]]


def test_visit_session_column_defaults():
    import models
    col = models.VisitSession.__table__.columns["status"]
    assert col.default is not None


def test_event_model():
    import models
    now = datetime.datetime.now(datetime.timezone.utc)
    event = models.Event(
        event_type="ENTRY",
        identity_type="KNOWN",
        person_id=1,
        track_id=42,
        camera_id=1,
        timestamp=now,
        confidence=0.95,
    )
    assert event.event_type == "ENTRY"
    assert event.identity_type == "KNOWN"
    assert event.track_id == 42
    assert event.confidence == 0.95


def test_audit_log():
    import models
    log = models.AuditLog(action="test", entity_type="person", entity_id=1)
    assert log.action == "test"
    assert log.entity_type == "person"


def test_vector_type_to_list():
    from models import VectorType
    vt = VectorType(dim=128)
    value = [0.1, 0.2, 0.3]
    class MockSQLiteDialect:
        name = "sqlite"
    result = vt.process_bind_param(value, MockSQLiteDialect())
    assert json.loads(result) == [0.1, 0.2, 0.3]


def test_vector_type_from_list_sqlite():
    from models import VectorType
    vt = VectorType(dim=128)
    class MockSQLiteDialect:
        name = "sqlite"
    result = vt.process_result_value(json.dumps([0.1, 0.2, 0.3]), MockSQLiteDialect())
    assert result == [0.1, 0.2, 0.3]


def test_vector_type_from_numpy():
    from models import VectorType
    vt = VectorType(dim=128)
    class MockSQLiteDialect:
        name = "sqlite"
    arr = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    result = vt.process_bind_param(arr, MockSQLiteDialect())
    parsed = json.loads(result)
    assert len(parsed) == 3
    assert parsed[0] == pytest.approx(0.1, abs=1e-6)


def test_vector_type_null():
    from models import VectorType
    vt = VectorType(dim=128)
    class MockSQLiteDialect:
        name = "sqlite"
    assert vt.process_bind_param(None, MockSQLiteDialect()) is None
    assert vt.process_result_value(None, MockSQLiteDialect()) is None


def test_vector_type_numpy_string():
    from models import VectorType
    vt = VectorType(dim=128)
    class MockSQLiteDialect:
        name = "sqlite"
    value = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    result = vt.process_bind_param(value, MockSQLiteDialect())
    parsed = json.loads(result)
    assert len(parsed) == 3


def test_person_relationships():
    import models
    person = models.Person(full_name="Bob", member_code="SV002", role="STUDENT")
    assert hasattr(person, "face_templates")
    assert hasattr(person, "events")
    assert hasattr(person, "visit_sessions")


def test_visit_session_status_values():
    import models
    col = models.VisitSession.__table__.columns["status"]
    assert col.nullable is False
    assert col.default is not None


def test_vector_type_postgres_roundtrip():
    from models import VectorType
    vt = VectorType(dim=128)
    class MockPGDialect:
        name = "postgresql"
    value = [0.1, 0.2, 0.3]
    bound = vt.process_bind_param(value, MockPGDialect())
    assert bound == value


def test_face_template_embedding_required():
    import models
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    template = models.FaceTemplate(
        person_id=1,
        embedding_vector=[0.5] * 128,
        created_at=now,
    )
    assert len(template.embedding_vector) == 128


def test_camera_config_json_fields():
    import models
    config = models.CameraConfig(
        camera_id=1,
        entry_line_config=[[10, 20], [100, 200]],
        exit_line_config=[[10, 200], [100, 20]],
        inside_zone_config=[[10, 20], [100, 200]],
    )
    assert config.entry_line_config == [[10, 20], [100, 200]]
    assert config.inside_zone_config == [[10, 20], [100, 200]]


def test_user_model_required_fields():
    import models
    user = models.User(username="test_user", password_hash="hash", role="LIBRARIAN")
    assert user.username == "test_user"
    assert user.password_hash == "hash"
    assert user.role == "LIBRARIAN"


def test_person_model_required_fields():
    import models
    person = models.Person(full_name="Alice", member_code="SV001", role="STUDENT")
    assert person.full_name == "Alice"
    assert person.member_code == "SV001"
    assert person.role == "STUDENT"


def test_unknown_identity_required_fields():
    import models
    now = datetime.datetime.now(datetime.timezone.utc)
    unk = models.UnknownIdentity(
        anonymous_code="UNKNOWN_20260710_0001",
        embedding_vector=[0.1, 0.2, 0.3],
        expire_at=now,
    )
    assert unk.anonymous_code == "UNKNOWN_20260710_0001"
    assert unk.embedding_vector == [0.1, 0.2, 0.3]
    assert unk.expire_at == now
