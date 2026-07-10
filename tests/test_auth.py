from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from auth import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
    get_current_user, require_user, require_admin,
)
from models import User


def test_hash_and_verify():
    hashed = hash_password("test123")
    assert hashed != "test123"
    assert verify_password("test123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_token():
    token = create_access_token({"sub": "1", "role": "ADMIN"})
    assert token is not None
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["role"] == "ADMIN"


def test_decode_invalid_token():
    assert decode_access_token("invalid-token") is None


def test_decode_expired_token():
    token = create_access_token({"sub": "1"}, expires_delta=-1)
    assert decode_access_token(token) is None


def test_get_current_user_no_credentials():
    result = get_current_user(None, MagicMock())
    assert result is None


def test_get_current_user_invalid_token():
    creds = MagicMock()
    creds.credentials = "bad-token"
    result = get_current_user(creds, MagicMock())
    assert result is None


def test_get_current_user_valid_token():
    token = create_access_token({"sub": "42", "role": "LIBRARIAN"})
    creds = MagicMock()
    creds.credentials = token

    mock_db = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    result = get_current_user(creds, mock_db)
    assert result == mock_user


def test_get_current_user_inactive():
    token = create_access_token({"sub": "42", "role": "LIBRARIAN"})
    creds = MagicMock()
    creds.credentials = token

    mock_db = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    result = get_current_user(creds, mock_db)
    assert result is None


def test_require_user_raises_when_none():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        require_user(None)
    assert exc.value.status_code == 401


def test_require_user_returns_user():
    mock_user = MagicMock(spec=User)
    assert require_user(mock_user) == mock_user


def test_require_admin_raises_when_not_admin():
    import pytest
    from fastapi import HTTPException
    mock_user = MagicMock(spec=User)
    mock_user.role = "LIBRARIAN"
    with pytest.raises(HTTPException) as exc:
        require_admin(mock_user)
    assert exc.value.status_code == 403


def test_require_admin_passes():
    mock_user = MagicMock(spec=User)
    mock_user.role = "ADMIN"
    assert require_admin(mock_user) == mock_user


def test_token_with_custom_expiry():
    token = create_access_token({"sub": "1"}, expires_delta=1)
    payload = decode_access_token(token)
    assert payload is not None


def test_password_hash_different():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt uses different salts


@patch("auth.ACCESS_TOKEN_EXPIRE_MINUTES", 60)
def test_use_env_expiry():
    token = create_access_token({"sub": "1"})
    assert decode_access_token(token) is not None
