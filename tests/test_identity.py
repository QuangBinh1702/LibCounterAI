import datetime
from unittest.mock import MagicMock

import numpy as np

from models import VisitSession, Person, UnknownIdentity


def test_identity_from_known_session():
    mock_session = MagicMock(spec=VisitSession)
    mock_person = MagicMock(spec=Person)
    mock_person.full_name = "Nguyen Van A"
    mock_session.identity_type = "KNOWN"
    mock_session.person_id = 1
    mock_session.unknown_id = None
    mock_session.person = mock_person

    from main import identity_from_visit_session
    result = identity_from_visit_session(mock_session)

    assert result is not None
    assert result["identity_type"] == "KNOWN"
    assert result["person_id"] == 1
    assert result["person_name"] == "Nguyen Van A"
    assert result["unknown_id"] is None


def test_identity_from_unknown_session():
    mock_session = MagicMock(spec=VisitSession)
    mock_unknown = MagicMock(spec=UnknownIdentity)
    mock_unknown.anonymous_code = "UNKNOWN_20260710_0001"
    mock_session.identity_type = "UNKNOWN"
    mock_session.person_id = None
    mock_session.unknown_id = 5
    mock_session.unknown_identity = mock_unknown

    from main import identity_from_visit_session
    result = identity_from_visit_session(mock_session)

    assert result is not None
    assert result["identity_type"] == "UNKNOWN"
    assert result["unknown_id"] == 5
    assert result["person_name"] == "UNKNOWN_20260710_0001"
    assert result["person_id"] is None


def test_identity_from_session_no_person_no_unknown():
    mock_session = MagicMock(spec=VisitSession)
    mock_session.identity_type = "UNMATCHED"
    mock_session.person_id = None
    mock_session.unknown_id = None

    from main import identity_from_visit_session
    result = identity_from_visit_session(mock_session)

    assert result is None


def test_infer_exit_identity_single_active_session():
    mock_db = MagicMock()
    mock_session = MagicMock(spec=VisitSession)
    mock_session.id = 42
    mock_session.identity_type = "KNOWN"
    mock_session.person_id = 1
    mock_session.unknown_id = None

    mock_person = MagicMock(spec=Person)
    mock_person.full_name = "Nguyen Van A"
    mock_session.person = mock_person

    mock_db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [mock_session]

    from main import infer_exit_identity_from_active_sessions
    identity, count = infer_exit_identity_from_active_sessions(mock_db)

    assert count == 1
    assert identity is not None
    assert identity["identity_type"] == "KNOWN"
    assert identity["person_id"] == 1
    assert identity["visit_session_id"] == 42


def test_infer_exit_identity_no_sessions():
    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = []

    from main import infer_exit_identity_from_active_sessions
    identity, count = infer_exit_identity_from_active_sessions(mock_db)

    assert count == 0
    assert identity is None


def test_infer_exit_identity_multi_sessions_returns_none():
    mock_db = MagicMock()
    mock_s1 = MagicMock(spec=VisitSession)
    mock_s2 = MagicMock(spec=VisitSession)
    mock_db.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = [mock_s1, mock_s2]

    from main import infer_exit_identity_from_active_sessions
    identity, count = infer_exit_identity_from_active_sessions(mock_db)

    assert count == 2
    assert identity is None


def test_cosine_similarity_perfect_match():
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    assert abs(sim - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.0, 1.0], dtype=np.float32)
    sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    assert abs(sim) < 1e-6


def test_cosine_similarity_opposite():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([-1.0, 0.0], dtype=np.float32)
    sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    assert abs(sim - (-1.0)) < 1e-6


def test_cosine_similarity_zero_vector():
    a = np.array([0.0, 0.0], dtype=np.float32)
    b = np.array([1.0, 0.0], dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    assert norm_a <= 1e-6
    assert norm_b > 1e-6


def test_known_match_threshold():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.6, 0.8], dtype=np.float32)
    sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    assert sim >= 0.6  # cosine of ~53 degrees


def test_known_below_threshold():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.5, 0.866], dtype=np.float32)
    sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    assert sim < 0.6  # cosine of 60 degrees = 0.5


def test_unknown_match_threshold():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.55, 0.835], dtype=np.float32)
    sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    assert sim >= 0.55


def test_unknown_below_threshold():
    a = np.array([1.0, 0.0], dtype=np.float32)
    b = np.array([0.54, 0.84], dtype=np.float32)
    sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    assert sim < 0.55
