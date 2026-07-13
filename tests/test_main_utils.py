import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.datastructures import UploadFile


def test_utc_now():
    from main import utc_now
    now = utc_now()
    assert now.tzinfo == datetime.timezone.utc


def test_as_vietnam_time_naive():
    from main import as_vietnam_time, VIETNAM_TZ
    naive = datetime.datetime(2026, 7, 10, 12, 0, 0)
    result = as_vietnam_time(naive)
    assert result.tzinfo is not None
    assert result.utcoffset() == datetime.timedelta(hours=7)


def test_as_vietnam_time_utc():
    from main import as_vietnam_time, VIETNAM_TZ
    utc_dt = datetime.datetime(2026, 7, 10, 12, 0, 0, tzinfo=datetime.timezone.utc)
    result = as_vietnam_time(utc_dt)
    assert result.hour == 19


def test_local_day_start_as_utc():
    from main import local_day_start_as_utc
    vietnam_dt = datetime.datetime(2026, 7, 10, 12, 0, 0)
    result = local_day_start_as_utc(vietnam_dt)
    assert result.tzinfo is None
    assert result.day == 10


def test_elapsed_seconds_basic():
    from main import elapsed_seconds
    start = datetime.datetime(2026, 7, 10, 10, 0, 0, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(2026, 7, 10, 12, 30, 0, tzinfo=datetime.timezone.utc)
    assert elapsed_seconds(start, end) == 9000


def test_elapsed_seconds_naive_input():
    from main import elapsed_seconds
    start = datetime.datetime(2026, 7, 10, 10, 0, 0)
    end = datetime.datetime(2026, 7, 10, 10, 0, 30)
    assert elapsed_seconds(start, end) == 30


def test_parse_bool_true_values():
    from main import parse_bool
    assert parse_bool("true") is True
    assert parse_bool("1") is True
    assert parse_bool("yes") is True
    assert parse_bool("on") is True
    assert parse_bool(True) is True


def test_parse_bool_false_values():
    from main import parse_bool
    assert parse_bool("false") is False
    assert parse_bool("0") is False
    assert parse_bool("no") is False
    assert parse_bool("off") is False
    assert parse_bool(False) is False


def test_parse_bool_none():
    from main import parse_bool
    assert parse_bool(None) is False
    assert parse_bool(None, default=True) is True


def test_parse_float_valid():
    from main import parse_float
    assert parse_float("3.14", 0.0) == 3.14
    assert parse_float("0", 1.0) == 0.0


def test_parse_float_invalid():
    from main import parse_float
    assert parse_float("abc", 1.5) == 1.5
    assert parse_float(None, 2.0) == 2.0


def test_cors_headers():
    from main import cors_headers
    request = MagicMock()
    request.headers.get.return_value = "http://example.com"
    headers = cors_headers(request)
    assert headers["Access-Control-Allow-Origin"] == "http://example.com"
    assert headers["Vary"] == "Origin"


def test_cors_headers_no_origin():
    from main import cors_headers
    request = MagicMock()
    request.headers.get.return_value = None
    headers = cors_headers(request)
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_invalidate_face_template_cache():
    from main import face_template_cache, invalidate_face_template_cache
    face_template_cache["loaded_at"] = 123.0
    face_template_cache["items"] = [{"person_id": 1}]
    invalidate_face_template_cache()
    assert face_template_cache["loaded_at"] == 0.0
    assert face_template_cache["items"] == []


def test_paginate():
    from main import paginate
    query = MagicMock()
    query.count.return_value = 42
    query.offset.return_value.limit.return_value.all.return_value = ["a", "b"]
    items, total = paginate(query, skip=10, limit=20)
    assert items == ["a", "b"]
    assert total == 42
    query.offset.assert_called_once_with(10)
    query.offset.return_value.limit.assert_called_once_with(20)


def test_identity_from_visit_session_known():
    from main import identity_from_visit_session
    person = MagicMock()
    person.full_name = "Alice"
    session = MagicMock()
    session.identity_type = "KNOWN"
    session.person_id = 1
    session.person = person
    session.unknown_id = None
    result = identity_from_visit_session(session)
    assert result["identity_type"] == "KNOWN"
    assert result["person_id"] == 1
    assert result["person_name"] == "Alice"
    assert result["unknown_id"] is None


def test_identity_from_visit_session_unknown():
    from main import identity_from_visit_session
    unknown = MagicMock()
    unknown.anonymous_code = "UNKNOWN_20260710_0001"
    session = MagicMock()
    session.identity_type = "UNKNOWN"
    session.unknown_id = 5
    session.unknown_identity = unknown
    session.person_id = None
    session.person = None
    result = identity_from_visit_session(session)
    assert result["identity_type"] == "UNKNOWN"
    assert result["unknown_id"] == 5
    assert result["person_name"] == "UNKNOWN_20260710_0001"


def test_identity_from_visit_session_none():
    from main import identity_from_visit_session
    session = MagicMock()
    session.identity_type = "KNOWN"
    session.person_id = None
    result = identity_from_visit_session(session)
    assert result is None


def test_infer_exit_identity_single_active():
    from main import infer_exit_identity_from_active_sessions
    db = MagicMock()
    session = MagicMock()
    session.identity_type = "KNOWN"
    session.person_id = 1
    session.unknown_id = None
    session.id = 42
    person = MagicMock()
    person.full_name = "Bob"
    session.person = person
    session.unknown_identity = None
    db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [session]
    identity, count = infer_exit_identity_from_active_sessions(db)
    assert count == 1
    assert identity["visit_session_id"] == 42
    assert identity["person_id"] == 1


def test_infer_exit_identity_multiple():
    from main import infer_exit_identity_from_active_sessions
    db = MagicMock()
    db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [MagicMock(), MagicMock()]
    identity, count = infer_exit_identity_from_active_sessions(db)
    assert identity is None
    assert count == 2


def test_infer_exit_identity_none():
    from main import infer_exit_identity_from_active_sessions
    db = MagicMock()
    db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = []
    identity, count = infer_exit_identity_from_active_sessions(db)
    assert identity is None
    assert count == 0


@patch("main.ALLOWED_IMAGE_TYPES", {"image/jpeg", "image/png"})
@patch("main.MAX_UPLOAD_SIZE_MB", 10)
@pytest.mark.anyio
async def test_validate_image_file_jpeg():
    from main import validate_image_file
    file = MagicMock(spec=UploadFile)
    file.content_type = "image/jpeg"
    file.read = AsyncMock(return_value=b"\xff\xd8\xff\xe0" + b"\x00" * 64)
    result = await validate_image_file(file)
    assert len(result) > 0


@patch("main.ALLOWED_IMAGE_TYPES", {"image/jpeg", "image/png"})
@pytest.mark.anyio
async def test_validate_image_file_invalid_type():
    from main import validate_image_file
    file = MagicMock(spec=UploadFile)
    file.content_type = "application/pdf"
    with pytest.raises(HTTPException) as exc:
        await validate_image_file(file)
    assert exc.value.status_code == 400


@patch("main.ALLOWED_IMAGE_TYPES", {"image/jpeg", "image/png"})
@pytest.mark.anyio
async def test_validate_image_file_no_content_type():
    from main import validate_image_file
    file = MagicMock(spec=UploadFile)
    file.content_type = None
    file.read = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    result = await validate_image_file(file)
    assert len(result) > 0


@patch("main.ALLOWED_IMAGE_TYPES", {"image/jpeg", "image/png"})
@pytest.mark.anyio
async def test_validate_image_file_invalid_signature():
    from main import validate_image_file
    file = MagicMock(spec=UploadFile)
    file.content_type = "image/jpeg"
    file.read = AsyncMock(return_value=b"\x00\x00\x00\x00" + b"\x00" * 64)
    with pytest.raises(HTTPException) as exc:
        await validate_image_file(file)
    assert exc.value.status_code == 400


@patch("main.ALLOWED_IMAGE_TYPES", {"image/jpeg", "image/png"})
@pytest.mark.anyio
async def test_validate_image_file_too_small():
    from main import validate_image_file
    file = MagicMock(spec=UploadFile)
    file.content_type = "image/jpeg"
    file.read = AsyncMock(return_value=b"\xff\xd8\xff\xe0")
    with pytest.raises(HTTPException) as exc:
        await validate_image_file(file)
    assert exc.value.status_code == 400


def test_resolve_report_window_defaults():
    from main import resolve_report_window, VIETNAM_TZ
    start, end = resolve_report_window()
    assert isinstance(start, datetime.datetime)
    assert end > start
    assert start.tzinfo is None
    assert end.tzinfo is None


def test_resolve_report_window_specific_date():
    from main import resolve_report_window
    start, end = resolve_report_window(date="2026-07-10")
    assert start.month == 7
    assert start.day in (9, 10)
    assert end > start
    assert end.tzinfo is None


def test_resolve_report_window_range():
    from main import resolve_report_window
    start, end = resolve_report_window(from_date="2026-07-01", to_date="2026-07-10")
    assert isinstance(start, datetime.datetime)
    assert isinstance(end, datetime.datetime)
    assert end > start


def test_resolve_report_window_swapped():
    from main import resolve_report_window
    start, end = resolve_report_window(from_date="2026-07-10", to_date="2026-07-01")
    assert isinstance(start, datetime.datetime)
    assert end > start


def test_log_info_unicode():
    from main import log_info
    log_info("Test Unicode: Tiếng Việt")
    assert True


@patch("main.AUDIT_LOG_ENABLED", True)
def test_audit_log():
    from main import audit_log
    db = MagicMock()
    audit_log(db, "test_action", "test_entity", entity_id=1, actor="tester", details={"key": "val"})
    db.add.assert_called_once()
    db.commit.assert_called_once()
    added = db.add.call_args[0][0]
    assert added.action == "test_action"
    assert added.entity_type == "test_entity"
    assert added.entity_id == 1
    assert added.actor == "tester"


@patch("main.AUDIT_LOG_ENABLED", False)
def test_audit_log_disabled():
    from main import audit_log
    db = MagicMock()
    audit_log(db, "test_action", "test_entity")
    db.add.assert_not_called()
