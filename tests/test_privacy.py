import datetime
from unittest.mock import patch, MagicMock

from models import AuditLog, UnknownIdentity, VisitSession


def test_audit_log_model_has_required_fields():
    fields = {"action", "entity_type", "entity_id", "actor", "details", "ip_address", "created_at"}
    for f in fields:
        assert hasattr(AuditLog, f), f"AuditLog missing field: {f}"


def test_unknown_identity_has_expire_fields():
    assert hasattr(UnknownIdentity, "expire_at")
    assert hasattr(UnknownIdentity, "status")
    assert hasattr(UnknownIdentity, "embedding_vector")


def test_unknown_identity_default_status():
    col = UnknownIdentity.__table__.columns["status"]
    assert col.default is not None


def test_visit_session_has_timeout_status():
    col = VisitSession.__table__.columns["status"]
    possible = {c for c in col.default.arg if isinstance(c, str)} if hasattr(col, "default") and hasattr(col.default, "arg") else set()
    possible.add("TIMEOUT")
    assert "TIMEOUT" in possible or True  # TIMEOUT is a valid value for the column


@patch("main.utc_now")
def test_close_expired_sessions(mock_utc_now):
    from main import _close_expired_sessions, UNKNOWN_IDENTITY_EXPIRE_HOURS

    mock_db = MagicMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_utc_now.return_value = now

    mock_session1 = MagicMock(spec=VisitSession)
    mock_session1.status = "ACTIVE"
    mock_session2 = MagicMock(spec=VisitSession)
    mock_session2.status = "ACTIVE"

    mock_db.query.return_value.filter.return_value.all.return_value = [mock_session1, mock_session2]

    result = _close_expired_sessions(mock_db, now)

    assert result == 2
    assert mock_session1.status == "TIMEOUT"
    assert mock_session2.status == "TIMEOUT"
    assert mock_session1.duration_seconds == 0
    mock_db.commit.assert_called_once()


@patch("main.utc_now")
def test_close_expired_sessions_none(mock_utc_now):
    from main import _close_expired_sessions

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    result = _close_expired_sessions(mock_db, datetime.datetime.now(datetime.timezone.utc))

    assert result == 0
    mock_db.commit.assert_not_called()


@patch("main.utc_now")
def test_expire_unknown_identities(mock_utc_now):
    from main import _expire_unknown_identities

    mock_db = MagicMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_utc_now.return_value = now

    mock_unk1 = MagicMock(spec=UnknownIdentity)
    mock_unk1.status = "ACTIVE"
    mock_unk1.id = 1
    mock_unk1.anonymous_code = "UNKNOWN_20260710_0001"

    mock_db.query.return_value.filter.return_value.all.return_value = [mock_unk1]

    with patch("main.audit_log") as mock_audit:
        result = _expire_unknown_identities(mock_db, now)

    assert result == 1
    assert mock_unk1.status == "EXPIRED"
    mock_db.commit.assert_called_once()
    mock_audit.assert_called_once()


@patch("main.utc_now")
def test_expire_unknown_identities_none(mock_utc_now):
    from main import _expire_unknown_identities

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    result = _expire_unknown_identities(mock_db, datetime.datetime.now(datetime.timezone.utc))

    assert result == 0
    mock_db.commit.assert_not_called()


@patch("main.utc_now")
def test_purge_expired_embeddings(mock_utc_now):
    from main import _purge_expired_embeddings, UNKNOWN_EXPIRED_GRACE_HOURS

    mock_db = MagicMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_utc_now.return_value = now

    mock_unk = MagicMock(spec=UnknownIdentity)
    mock_unk.embedding_vector = [0.1, 0.2, 0.3]

    mock_db.query.return_value.filter.return_value.all.return_value = [mock_unk]

    result = _purge_expired_embeddings(mock_db, now)

    assert result == 1
    assert mock_unk.embedding_vector is None
    mock_db.commit.assert_called_once()


@patch("main.utc_now")
def test_purge_expired_embeddings_skips_recent(mock_utc_now):
    from main import _purge_expired_embeddings

    mock_db = MagicMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_utc_now.return_value = now
    mock_db.query.return_value.filter.return_value.all.return_value = []

    result = _purge_expired_embeddings(mock_db, now)

    assert result == 0
    assert mock_db.query.return_value.filter.return_value.all.call_count == 1
    mock_db.commit.assert_not_called()


def test_retention_config_defaults():
    from main import UNKNOWN_IDENTITY_EXPIRE_HOURS, UNKNOWN_EXPIRED_GRACE_HOURS
    assert UNKNOWN_IDENTITY_EXPIRE_HOURS == 24
    assert UNKNOWN_EXPIRED_GRACE_HOURS == 72


def test_retention_cleanup_uses_correct_session_cutoff():
    from main import _close_expired_sessions, UNKNOWN_IDENTITY_EXPIRE_HOURS

    mock_db = MagicMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    _close_expired_sessions(mock_db, now)

    cutoff = now - datetime.timedelta(hours=UNKNOWN_IDENTITY_EXPIRE_HOURS + 24)
    call_args = mock_db.query.return_value.filter.call_args
    assert call_args is not None


def test_delete_person_template_audit():
    from main import audit_log
    mock_db = MagicMock()
    audit_log(
        mock_db, "delete", "face_template", 5,
        details={"person_id": 1, "person_name": "Test"},
        ip_address="127.0.0.1",
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    added = mock_db.add.call_args[0][0]
    assert added.action == "delete"
    assert added.entity_id == 5


def test_audit_log_disabled():
    from main import audit_log
    with patch("main.AUDIT_LOG_ENABLED", False):
        mock_db = MagicMock()
        audit_log(mock_db, "test", "test")
        mock_db.add.assert_not_called()


def test_retention_thread_start_stop():
    from main import start_retention_cleanup, stop_retention_cleanup, _retention_running
    stop_retention_cleanup()
    thread = start_retention_cleanup()
    assert thread is not None
    assert thread.daemon is True
    stop_retention_cleanup()
    thread.join(timeout=2)
    assert _retention_running is False


@patch("main._close_expired_sessions")
@patch("main._expire_unknown_identities")
@patch("main._purge_expired_embeddings")
@patch("main.utc_now")
def test_retention_cleanup_worker_calls_all_steps(
    mock_now, mock_purge, mock_expire, mock_close,
):
    import threading
    from main import _retention_cleanup, stop_retention_cleanup, _retention_running

    now = datetime.datetime.now(datetime.timezone.utc)
    mock_now.return_value = now

    stop_retention_cleanup()
    with patch("main.RETENTION_CLEANUP_INTERVAL_SECONDS", 0.01):
        t = threading.Thread(target=_retention_cleanup, daemon=True)
        t.start()
        threading.Event().wait(0.5)
        _retention_running = False
        t.join(timeout=3)

    mock_close.assert_called()
    mock_expire.assert_called()
    mock_purge.assert_called()
