from unittest.mock import MagicMock, patch


@patch("sync_service.models")
def test_replay_op_event_insert(mock_models):
    from sync_service import _replay_op
    db = MagicMock()
    op = {
        "id": 1,
        "table_name": "events",
        "operation": "INSERT",
        "data": {
            "event_type": "ENTRY",
            "identity_type": "KNOWN",
            "person_id": 1,
            "unknown_id": None,
            "track_id": 42,
            "camera_id": 1,
            "confidence": 0.95,
            "timestamp": "2026-07-10T10:00:00+00:00",
            "metadata_json": {"resolution": "face"},
        },
    }
    result = _replay_op(op, db)
    assert result is True
    mock_models.Event.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called_once()


@patch("sync_service.models")
def test_replay_op_event_insert_with_session(mock_models):
    from sync_service import _replay_op
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None
    op = {
        "id": 1,
        "table_name": "events",
        "operation": "INSERT",
        "data": {
            "event_type": "ENTRY",
            "identity_type": "UNKNOWN",
            "person_id": None,
            "unknown_id": 5,
            "track_id": 99,
            "camera_id": 1,
            "confidence": 0.85,
            "timestamp": "2026-07-10T10:00:00+00:00",
            "metadata_json": None,
            "visit_session_data": {
                "identity_type": "UNKNOWN",
                "unknown_id": 5,
                "entry_camera_id": 1,
                "entry_at": "2026-07-10T10:00:00+00:00",
                "status": "ACTIVE",
            },
        },
    }
    result = _replay_op(op, db)
    assert result is True
    assert mock_models.Event.call_count == 1
    mock_models.VisitSession.assert_called_once()
    db.add.assert_called()


@patch("sync_service.models")
def test_replay_op_unknown_identity_insert(mock_models):
    from sync_service import _replay_op
    db = MagicMock()
    op = {
        "id": 2,
        "table_name": "unknown_identities",
        "operation": "INSERT",
        "data": {
            "anonymous_code": "UNKNOWN_20260710_0001",
            "embedding_vector": [0.1, 0.2, 0.3],
            "expire_at": "2026-07-11T10:00:00+00:00",
            "status": "ACTIVE",
            "visit_count": 1,
            "created_at": "2026-07-10T10:00:00+00:00",
            "last_seen_at": "2026-07-10T10:00:00+00:00",
        },
    }
    result = _replay_op(op, db)
    assert result is True
    mock_models.UnknownIdentity.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called_once()


@patch("sync_service.models")
def test_replay_op_person_insert(mock_models):
    from sync_service import _replay_op
    db = MagicMock()
    mock_person = MagicMock()
    mock_person.id = 1
    mock_models.Person.return_value = mock_person
    op = {
        "id": 3,
        "table_name": "persons",
        "operation": "INSERT",
        "data": {
            "full_name": "Alice",
            "member_code": "SV001",
            "role": "STUDENT",
            "status": "ACTIVE",
            "face_template": {
                "embedding_vector": [0.1, 0.2, 0.3],
                "quality_score": 0.95,
            },
        },
    }
    result = _replay_op(op, db)
    assert result is True
    mock_models.Person.assert_called_once_with(
        full_name="Alice", member_code="SV001", role="STUDENT", status="ACTIVE"
    )
    mock_models.FaceTemplate.assert_called_once()
    assert db.add.call_count == 2


@patch("sync_service.models")
def test_replay_op_visit_session_update(mock_models):
    from sync_service import _replay_op
    db = MagicMock()
    mock_sess = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = mock_sess
    op = {
        "id": 4,
        "table_name": "visit_sessions",
        "operation": "UPDATE",
        "data": {"id": 10, "status": "CLOSED", "exit_at": "2026-07-10T12:00:00+00:00"},
    }
    result = _replay_op(op, db)
    assert result is True
    assert mock_sess.status == "CLOSED"
    db.commit.assert_called_once()


@patch("sync_service.models")
def test_replay_op_failure_handled(mock_models):
    from sync_service import _replay_op
    db = MagicMock()
    db.add.side_effect = ValueError("DB error")
    op = {
        "id": 99,
        "table_name": "events",
        "operation": "INSERT",
        "data": {"event_type": "ENTRY", "track_id": 1, "camera_id": 1, "timestamp": "2026-07-10T10:00:00+00:00"},
    }
    result = _replay_op(op, db)
    assert result is False


@patch("sync_service.is_postgres_alive")
@patch("sync_service.get_pending")
@patch("sync_service.SessionLocal")
@patch("sync_service._replay_op")
def test_sync_loop_processes_ops(mock_replay, mock_session_local, mock_get_pending, mock_alive):
    from sync_service import sync_loop, stop, _running
    mock_alive.return_value = True
    mock_get_pending.return_value = [
        {"id": 1, "table_name": "events", "operation": "INSERT", "data": {}, "retries": 0},
    ]
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db
    mock_replay.return_value = True

    from sync_service import SYNC_INTERVAL_SECONDS
    with patch.object(__import__("sync_service"), "SYNC_INTERVAL_SECONDS", 0.01):
        import threading
        t = threading.Thread(target=sync_loop, daemon=True)
        t.start()
        import time
        time.sleep(0.1)
        stop()
        t.join(timeout=2)

    mock_replay.assert_called()
    mock_db.close.assert_called()


@patch("sync_service.count_pending")
@patch("sync_service.is_postgres_alive")
def test_get_status(mock_alive, mock_count):
    from sync_service import get_status, start, stop
    mock_alive.return_value = True
    mock_count.return_value = 5
    stop()
    status = get_status()
    assert status["pending_count"] == 5
    assert status["postgres_alive"] is True
    assert status["running"] is False


@patch("sync_service.count_pending")
@patch("sync_service.is_postgres_alive")
def test_get_status_with_last_sync(mock_alive, mock_count):
    from sync_service import get_status, _last_sync_at
    import datetime
    _last_sync_at = datetime.datetime(2026, 7, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
    mock_alive.return_value = False
    mock_count.return_value = 0
    status = get_status()
    assert status["last_sync_at"] is not None


def test_start_stop():
    from sync_service import start, stop, _running
    stop()
    thread = start()
    assert thread is not None
    assert thread.daemon is True
    stop()
    thread.join(timeout=2)
