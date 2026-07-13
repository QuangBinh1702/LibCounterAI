import datetime
from unittest.mock import patch, MagicMock

import pytest

from models import AuditLog, UnknownIdentity, VisitSession


def test_audit_log_model_has_required_fields():
    fields = {"action", "entity_type", "entity_id", "actor", "details", "ip_address", "created_at"}
    for f in fields:
        assert hasattr(AuditLog, f), f"AuditLog missing field: {f}"


def test_unknown_identity_has_expire_fields():
    assert hasattr(UnknownIdentity, "expire_at")
    assert hasattr(UnknownIdentity, "status")
    assert hasattr(UnknownIdentity, "embedding_vector")


def test_retention_config_defaults():
    from retention import read_config
    cfg = read_config()
    assert cfg["event_days"] == 365
    assert cfg["session_days"] == 365
    assert cfg["unknown_expire_hours"] == 24
    assert cfg["unknown_purge_days"] == 30
    assert cfg["template_grace_days"] == 90
    assert cfg["audit_log_days"] == 730


def test_config_reads_env():
    import retention as _ret
    with patch("retention.os.getenv") as mock_getenv:
        mock_getenv.side_effect = lambda k, d: {"RETENTION_EVENT_DAYS": "180"}.get(k, d)
        cfg = _ret.read_config()
        assert cfg["event_days"] == 180


def test_phase_timeout_sessions():
    mock_db = MagicMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_sess = MagicMock(spec=VisitSession)
    mock_sess.status = "ACTIVE"
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_sess]

    from retention import phase_timeout_sessions
    count = phase_timeout_sessions(mock_db, {"session_timeout_hours": 48}, now)

    assert count == 1
    assert mock_sess.status == "TIMEOUT"
    assert mock_sess.duration_seconds == 0
    mock_db.commit.assert_called_once()


def test_phase_timeout_sessions_none():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    from retention import phase_timeout_sessions
    count = phase_timeout_sessions(mock_db, {"session_timeout_hours": 48}, datetime.datetime.now(datetime.timezone.utc))

    assert count == 0
    mock_db.commit.assert_not_called()


def test_phase_expire_unknowns():
    mock_db = MagicMock()
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_unk = MagicMock(spec=UnknownIdentity)
    mock_unk.status = "ACTIVE"
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_unk]

    from retention import phase_expire_unknowns
    count = phase_expire_unknowns(mock_db, {"unknown_expire_hours": 24}, now)

    assert count == 1
    assert mock_unk.status == "EXPIRED"
    mock_db.commit.assert_called_once()


def test_phase_expire_unknowns_none():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []

    from retention import phase_expire_unknowns
    count = phase_expire_unknowns(mock_db, {"unknown_expire_hours": 24}, datetime.datetime.now(datetime.timezone.utc))

    assert count == 0
    mock_db.commit.assert_not_called()


def test_phase_purge_events():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.delete.return_value = 5

    from retention import phase_purge_events
    count = phase_purge_events(mock_db, {"event_days": 365}, datetime.datetime.now(datetime.timezone.utc))

    assert count == 5
    mock_db.commit.assert_called_once()


def test_phase_purge_events_none():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.delete.return_value = 0

    from retention import phase_purge_events
    count = phase_purge_events(mock_db, {"event_days": 365}, datetime.datetime.now(datetime.timezone.utc))

    assert count == 0
    mock_db.commit.assert_not_called()


def test_phase_purge_sessions():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.delete.return_value = 3

    from retention import phase_purge_sessions
    count = phase_purge_sessions(mock_db, {"session_days": 365}, datetime.datetime.now(datetime.timezone.utc))

    assert count == 3
    mock_db.commit.assert_called_once()


def test_phase_purge_templates():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.delete.return_value = 2

    from retention import phase_purge_templates
    count = phase_purge_templates(mock_db, {"template_grace_days": 90}, datetime.datetime.now(datetime.timezone.utc))

    assert count == 2
    mock_db.commit.assert_called_once()


def test_phase_purge_expired_unknowns():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.delete.return_value = 4

    from retention import phase_purge_expired_unknowns
    count = phase_purge_expired_unknowns(mock_db, {"unknown_purge_days": 30}, datetime.datetime.now(datetime.timezone.utc))

    assert count == 4
    mock_db.commit.assert_called_once()


def test_phase_purge_audit_log():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.delete.return_value = 10

    from retention import phase_purge_audit_log
    count = phase_purge_audit_log(mock_db, {"audit_log_days": 730}, datetime.datetime.now(datetime.timezone.utc))

    assert count == 10
    mock_db.commit.assert_called_once()


@patch("retention._write_audit")
def test_run_retention_dry_run(mock_write_audit):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.delete.return_value = 0
    mock_db.query.return_value.filter.return_value.count.return_value = 0

    from retention import run_retention
    results = run_retention(mock_db, dry_run=True, now=datetime.datetime.now(datetime.timezone.utc))

    assert len(results) == 7
    for r in results:
        assert r["dry_run"] is True
        assert r["error"] is None
    mock_write_audit.assert_not_called()


@patch("retention._write_audit")
def test_run_retention_executes(mock_write_audit):
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.delete.return_value = 0
    mock_db.query.return_value.filter.return_value.count.return_value = 0

    from retention import run_retention
    results = run_retention(mock_db, dry_run=False, now=datetime.datetime.now(datetime.timezone.utc))

    assert len(results) == 7
    for r in results:
        assert r["error"] is None


def test_count_pending():
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.count.return_value = 1
    mock_db.query.return_value.filter.return_value.count.return_value = 0

    from retention import count_pending
    counts = count_pending(mock_db)

    assert "active_unknowns" in counts
    assert "expired_unknowns_pending_purge" in counts
    assert "events_older_than_retention" in counts
    assert "sessions_older_than_retention" in counts
    assert "inactive_templates_pending_purge" in counts
    assert "audit_log_rows" in counts


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


def test_retention_cleanup_thread_integration():
    import threading
    from main import _retention_cleanup, stop_retention_cleanup, _retention_running

    stop_retention_cleanup()
    with patch("main.RETENTION_CLEANUP_INTERVAL_SECONDS", 0.01):
        t = threading.Thread(target=_retention_cleanup, daemon=True)
        t.start()
        threading.Event().wait(0.5)
        _retention_running = False
        t.join(timeout=3)

    assert _retention_running is False
