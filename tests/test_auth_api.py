import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from models import User
from database import get_db
from auth import require_user, require_admin, require_staff, hash_password


@pytest.fixture
def client():
    from main import app
    app.dependency_overrides.clear()
    return TestClient(app)


def make_user(**kwargs):
    u = MagicMock(spec=User)
    u.id = kwargs.get("id", 1)
    u.username = kwargs.get("username", "admin")
    u.role = kwargs.get("role", "ADMIN")
    u.status = kwargs.get("status", "ACTIVE")
    u.password_hash = kwargs.get("password_hash", hash_password("admin123"))
    return u


def override_get_db(mock_db):
    def gen():
        try:
            yield mock_db
        finally:
            pass
    return gen


def override_require_user(user):
    def dep(u=user):
        if u is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Not authenticated")
        return u
    return dep


def override_require_admin(user):
    def dep(u=user):
        from fastapi import HTTPException
        if u is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if u.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Admin role required")
        return u
    return dep


class TestLogin:
    def test_success(self, client):
        user = make_user()
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = user

        client.app.dependency_overrides[get_db] = override_get_db(db)
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["user"]["username"] == "admin"
        assert body["user"]["role"] == "ADMIN"

    def test_wrong_password(self, client):
        user = make_user(password_hash=hash_password("realpass"))
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = user

        client.app.dependency_overrides[get_db] = override_get_db(db)
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_inactive_user(self, client):
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None

        client.app.dependency_overrides[get_db] = override_get_db(db)
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 401


class TestRegister:
    def test_success(self, client):
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        admin = make_user()

        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_admin] = override_require_admin(admin)
        resp = client.post("/api/auth/register", json={
            "username": "newuser", "password": "newpass123", "role": "LIBRARIAN",
        })
        assert resp.status_code == 201
        assert resp.json()["username"] == "newuser"

    def test_duplicate(self, client):
        existing = make_user(username="existing")
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = existing
        admin = make_user()

        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_admin] = override_require_admin(admin)
        resp = client.post("/api/auth/register", json={
            "username": "existing", "password": "pass123",
        })
        assert resp.status_code == 409

    def test_forbidden_librarian(self, client):
        librarian = make_user(role="LIBRARIAN")
        client.app.dependency_overrides[require_admin] = override_require_admin(librarian)
        resp = client.post("/api/auth/register", json={
            "username": "u", "password": "pass123",
        })
        assert resp.status_code == 403


class TestAuthMe:
    def test_success(self, client):
        user = make_user()
        client.app.dependency_overrides[require_user] = override_require_user(user)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

    def test_unauthorized(self, client):
        client.app.dependency_overrides[require_user] = override_require_user(None)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


class TestPasswordChange:
    def test_success(self, client):
        user = make_user(password_hash=hash_password("oldpass"))
        db = MagicMock()

        client.app.dependency_overrides[require_user] = override_require_user(user)
        client.app.dependency_overrides[get_db] = override_get_db(db)
        resp = client.put("/api/auth/password", json={
            "current_password": "oldpass", "new_password": "newpass123",
        })
        assert resp.status_code == 200

    def test_wrong_current(self, client):
        user = make_user(password_hash=hash_password("realpass"))
        db = MagicMock()

        client.app.dependency_overrides[require_user] = override_require_user(user)
        client.app.dependency_overrides[get_db] = override_get_db(db)
        resp = client.put("/api/auth/password", json={
            "current_password": "wrong", "new_password": "newpass123",
        })
        assert resp.status_code == 400

    def test_short_password(self, client):
        user = make_user()
        db = MagicMock()

        client.app.dependency_overrides[require_user] = override_require_user(user)
        client.app.dependency_overrides[get_db] = override_get_db(db)
        resp = client.put("/api/auth/password", json={
            "current_password": "oldpass", "new_password": "12",
        })
        assert resp.status_code == 422


class TestListUsers:
    def test_success(self, client):
        admin = make_user()
        user2 = make_user(id=2, username="librarian", role="LIBRARIAN")
        db = MagicMock()
        db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [admin, user2]
        db.query.return_value.order_by.return_value.count.return_value = 2

        client.app.dependency_overrides[require_admin] = override_require_admin(admin)
        client.app.dependency_overrides[get_db] = override_get_db(db)
        resp = client.get("/api/auth/users")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_forbidden_librarian(self, client):
        librarian = make_user(role="LIBRARIAN")
        client.app.dependency_overrides[require_admin] = override_require_admin(librarian)
        resp = client.get("/api/auth/users")
        assert resp.status_code == 403


class TestPersonRoleGuard:
    def test_librarian_cannot_register_person(self, client):
        librarian = make_user(role="LIBRARIAN")
        db = MagicMock()
        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_admin] = override_require_admin(librarian)
        client.app.dependency_overrides[require_user] = override_require_user(librarian)
        resp = client.post("/api/persons/register", data={
            "full_name": "Test", "member_code": "T001", "role": "STUDENT",
        })
        assert resp.status_code == 403

    def test_librarian_cannot_update_person(self, client):
        librarian = make_user(role="LIBRARIAN")
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_admin] = override_require_admin(librarian)
        client.app.dependency_overrides[require_user] = override_require_user(librarian)
        resp = client.put("/api/persons/1", data={
            "full_name": "Test", "member_code": "T001", "role": "STUDENT",
        })
        assert resp.status_code == 403

    def test_librarian_cannot_delete_person(self, client):
        librarian = make_user(role="LIBRARIAN")
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_admin] = override_require_admin(librarian)
        resp = client.delete("/api/persons/1")
        assert resp.status_code == 403

    def test_admin_not_blocked_by_role_guard(self, client):
        admin = make_user()
        db = MagicMock()
        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_admin] = override_require_admin(admin)
        client.app.dependency_overrides[require_user] = override_require_user(admin)
        resp = client.post("/api/persons/register", data={
            "full_name": "Test", "member_code": "T001", "role": "STUDENT",
        })
        assert resp.status_code not in (401, 403)  # past role guard


class TestRetentionStaffAccess:
    def test_librarian_can_run_retention(self, client):
        librarian = make_user(role="LIBRARIAN")
        db = MagicMock()
        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_user] = override_require_user(librarian)

        def override_rs(user=librarian):
            if user is None:
                from fastapi import HTTPException
                raise HTTPException(status_code=401)
            if user.role not in ("ADMIN", "LIBRARIAN"):
                from fastapi import HTTPException
                raise HTTPException(status_code=403)
            return user
        client.app.dependency_overrides[require_staff] = override_rs
        resp = client.post("/api/admin/retention/run?dry_run=true")
        assert resp.status_code == 200

    def test_librarian_can_view_audit_log(self, client):
        librarian = make_user(role="LIBRARIAN")
        db = MagicMock()
        db.query.return_value.order_by.return_value.count.return_value = 0
        db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_user] = override_require_user(librarian)

        def override_rs(user=librarian):
            if user is None:
                from fastapi import HTTPException
                raise HTTPException(status_code=401)
            if user.role not in ("ADMIN", "LIBRARIAN"):
                from fastapi import HTTPException
                raise HTTPException(status_code=403)
            return user
        client.app.dependency_overrides[require_staff] = override_rs
        resp = client.get("/api/admin/audit-log")
        assert resp.status_code == 200


class TestPersonQualityGate:
    @patch("main.validate_image_file", new_callable=AsyncMock, return_value=b"fake")
    @patch("main.cv2.imdecode", return_value=np.zeros((100, 100, 3), dtype=np.uint8))
    @patch("main.face_pipeline")
    def test_register_quality_too_low(self, mock_fp, mock_imdecode, mock_validate, client):
        admin = make_user()
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None

        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_admin] = override_require_admin(admin)
        client.app.dependency_overrides[require_user] = override_require_user(admin)

        low_quality_face = MagicMock()
        low_quality_face.__getitem__.side_effect = lambda k: {
            "score": 0.5,
            "raw_face": np.zeros(15),
        }[k]
        mock_fp.detect_faces.return_value = [low_quality_face]

        resp = client.post(
            "/api/persons/register",
            data={
                "full_name": "Test",
                "member_code": "T001",
                "role": "STUDENT",
            },
            files={"file": ("test.jpg", b"fake", "image/jpeg")}
        )
        assert resp.status_code == 400
        assert "chất lượng" in resp.json()["detail"].lower()

    @patch("main.validate_image_file", new_callable=AsyncMock, return_value=b"fake")
    @patch("main.cv2.imdecode", return_value=np.zeros((100, 100, 3), dtype=np.uint8))
    @patch("main.face_pipeline")
    def test_register_quality_ok(self, mock_fp, mock_imdecode, mock_validate, client):
        admin = make_user()
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None

        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_admin] = override_require_admin(admin)
        client.app.dependency_overrides[require_user] = override_require_user(admin)

        good_face = MagicMock()
        good_face.__getitem__.side_effect = lambda k: {
            "score": 0.85,
            "raw_face": np.zeros(15),
        }[k]
        mock_fp.detect_faces.return_value = [good_face]
        mock_fp.extract_embedding.return_value = [0.1] * 128

        resp = client.post(
            "/api/persons/register",
            data={
                "full_name": "Test",
                "member_code": "T002",
                "role": "STUDENT",
            },
            files={"file": ("test.jpg", b"fake", "image/jpeg")}
        )
        assert resp.status_code == 201

    @patch("main.validate_image_file", new_callable=AsyncMock, return_value=b"fake")
    @patch("main.cv2.imdecode", return_value=np.zeros((100, 100, 3), dtype=np.uint8))
    @patch("main.face_pipeline")
    def test_update_quality_too_low(self, mock_fp, mock_imdecode, mock_validate, client):
        admin = make_user()
        mock_person = MagicMock()
        mock_person.id = 1

        mock_filter_by = MagicMock()
        mock_filter_by.first.return_value = mock_person
        mock_filter = MagicMock()
        mock_filter.first.return_value = None
        mock_query = MagicMock()
        mock_query.filter_by.return_value = mock_filter_by
        mock_query.filter.return_value = mock_filter

        db = MagicMock()
        db.query.return_value = mock_query
        client.app.dependency_overrides[get_db] = override_get_db(db)
        client.app.dependency_overrides[require_admin] = override_require_admin(admin)
        client.app.dependency_overrides[require_user] = override_require_user(admin)

        low_quality_face = MagicMock()
        low_quality_face.__getitem__.side_effect = lambda k: {
            "score": 0.5,
            "raw_face": np.zeros(15),
        }[k]
        mock_fp.detect_faces.return_value = [low_quality_face]

        resp = client.put(
            "/api/persons/1",
            data={
                "full_name": "Test",
                "member_code": "T001",
                "role": "STUDENT",
            },
            files={"file": ("test.jpg", b"fake", "image/jpeg")}
        )
        assert resp.status_code == 400
        assert "chất lượng" in resp.json()["detail"].lower()
