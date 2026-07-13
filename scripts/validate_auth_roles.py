import os, sys
CWD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(CWD, "app"))

from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from main import app
from database import get_db
from auth import require_user, require_admin, require_staff, hash_password
from models import User

results: list[str] = []
def check(name: str, ok: bool):
    results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}: {name}")

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
            raise HTTPException(status_code=401, detail="Not authenticated")
        return u
    return dep

def override_require_admin(user):
    def dep(u=user):
        if u is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if u.role != "ADMIN":
            raise HTTPException(status_code=403, detail="Admin role required")
        return u
    return dep

client = TestClient(app)
app.dependency_overrides.clear()
db = MagicMock()

print("=== Auth Roles Validation ===\n")

# 1. LIBRARIAN can view registry
librarian = make_user(role="LIBRARIAN")
app.dependency_overrides[get_db] = override_get_db(db)
app.dependency_overrides[require_user] = override_require_user(librarian)
resp = client.get("/api/persons")
check("LIBRARIAN can view registry (GET /api/persons)", resp.status_code == 200)

# 2. LIBRARIAN cannot create person
app.dependency_overrides[require_admin] = override_require_admin(librarian)
resp = client.post("/api/persons/register", data={"full_name": "Test", "member_code": "T001", "role": "STUDENT"})
check("LIBRARIAN cannot create person (POST /api/persons/register)", resp.status_code == 403)

# 3. LIBRARIAN cannot delete person
resp = client.delete("/api/persons/1")
check("LIBRARIAN cannot delete person (DELETE /api/persons/1)", resp.status_code == 403)

# 4. LIBRARIAN can run retention
app.dependency_overrides[require_admin] = override_require_admin(librarian)

def override_require_staff(user):
    def dep(u=user):
        if u is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if u.role not in ("ADMIN", "LIBRARIAN"):
            raise HTTPException(status_code=403, detail="Staff role required")
        return u
    return dep

app.dependency_overrides[require_staff] = override_require_staff(librarian)
resp = client.post("/api/admin/retention/run?dry_run=true")
check("LIBRARIAN can run retention (POST /api/admin/retention/run)", resp.status_code == 200)

# 5. LIBRARIAN can view audit log
resp = client.get("/api/admin/audit-log")
check("LIBRARIAN can view audit log (GET /api/admin/audit-log)", resp.status_code == 200)

# 6. LIBRARIAN cannot list users
resp = client.get("/api/auth/users")
check("LIBRARIAN cannot list users (GET /api/auth/users)", resp.status_code == 403)

# 7. LIBRARIAN cannot create user
resp = client.post("/api/auth/register", json={"username": "test", "password": "test123"})
check("LIBRARIAN cannot create user (POST /api/auth/register)", resp.status_code == 403)

# 8. ADMIN can do all
admin = make_user()
app.dependency_overrides[require_user] = override_require_user(admin)
app.dependency_overrides[require_admin] = override_require_admin(admin)
app.dependency_overrides[require_staff] = override_require_staff(admin)

resp = client.get("/api/persons")
check("ADMIN can view registry", resp.status_code == 200)

resp = client.get("/api/auth/users")
check("ADMIN can list users", resp.status_code == 200)

resp = client.post("/api/admin/retention/run?dry_run=true")
check("ADMIN can run retention", resp.status_code == 200)

resp = client.get("/api/admin/audit-log")
check("ADMIN can view audit log", resp.status_code == 200)

# 9. Password change
resp = client.put("/api/auth/password", json={"current_password": "admin123", "new_password": "newpass123"})
check("Password change succeeds with correct password", resp.status_code == 200)

resp = client.put("/api/auth/password", json={"current_password": "wrong", "new_password": "newpass123"})
check("Password change fails with wrong password", resp.status_code == 400)

# 10. User management
resp = client.put("/api/auth/users/2", json={"status": "INACTIVE"})
check("Admin can toggle user status", resp.status_code == 200)

resp = client.put("/api/auth/users/2", json={"role": "LIBRARIAN"})
check("Admin can change user role", resp.status_code == 200)

# 11. Enrollment quality gate
from main import MIN_ENROLLMENT_QUALITY as _q
check(f"MIN_ENROLLMENT_QUALITY = {_q} (>= 0.6)", _q >= 0.6)

from face_pipeline import FacePipeline
_default_threshold = FacePipeline.detect_faces.__defaults__[0]
check(f"FacePipeline default score_threshold = {_default_threshold}", _default_threshold >= 0.65)

print(f"\n=== Results: {sum(1 for _, ok in results if ok)}/{len(results)} passed ===\n")
for name, ok in results:
    print(f"  {'PASS' if ok else 'FAIL'}: {name}")

if all(ok for _, ok in results):
    print("\nAll auth role checks passed.")
    sys.exit(0)
else:
    print("\nSome auth role checks failed.")
    sys.exit(1)
