# Validation

## Proof Strategy

The story is proven when:
1. A LIBRARIAN user can log in, view registry (no edit/delete), run retention, view audit log, but cannot access user management or create persons.
2. An ADMIN user has full access to everything.
3. Password change works for any authenticated user.
4. User status/role mutation works for ADMIN only.
5. Backend 403 responses show proper toast on frontend.

## Test Plan

| Layer | Cases |
|-------|-------|
| Unit | `app/auth.py` — `require_staff` raises for LIBRARIAN? No, LIBRARIAN is allowed. `require_staff` raises for non-staff roles. |
| Integration | `POST /api/persons/register` as LIBRARIAN → 403; as ADMIN → 201. `PUT /api/auth/users/{id}` as LIBRARIAN → 403. `POST /api/admin/retention/run` as LIBRARIAN → 200. |
| E2E | Login as LIBRARIAN, verify registry has no edit/delete buttons, admin page has no "Người dùng" tab. |
| UI | Password change form renders, submits, succeeds. User management toggles status and role. |

## Fixtures

- One ADMIN user (existing seed).
- One LIBRARIAN user (new seed).
- One known person with face templates and sessions (existing seed).

## Commands

```text
.\.venv\Scripts\python.exe -m pytest tests/test_auth.py -v
.\.venv\Scripts\python.exe scripts/validate_auth_roles.py
```

## Acceptance Evidence

| Check | Method | Result |
|-------|--------|--------|
| LIBRARIAN can view registry | GET /api/persons returns 200 | ✅ PASS |
| LIBRARIAN cannot create person | POST /api/persons/register returns 403 | ✅ PASS |
| LIBRARIAN cannot update person | PUT /api/persons/{id} returns 403 | ✅ PASS |
| LIBRARIAN cannot delete person | DELETE /api/persons/{id} returns 403 | ✅ PASS |
| LIBRARIAN can run retention | POST /api/admin/retention/run returns 200 | ✅ PASS |
| LIBRARIAN can view audit log | GET /api/admin/audit-log returns 200 | ✅ PASS |
| LIBRARIAN cannot list users | GET /api/auth/users returns 403 | ✅ PASS |
| LIBRARIAN cannot create user | POST /api/auth/register returns 403 | ✅ PASS |
| ADMIN can do all the above | Each returns 200/201 | ✅ PASS |
| Password change succeeds | PUT /api/auth/password with correct current_password → 200 | ✅ PASS |
| Password change fails with wrong password | Same endpoint, wrong current_password → 400 | ✅ PASS |
| User status can be toggled | PUT /api/auth/users/{id} with status → 200 | ✅ PASS |
| Cannot deactivate last ADMIN | Trying to deactivate sole admin → 400 | ✅ PASS |
| Frontend hides write buttons for LIBRARIAN | RegistryPage "Sửa" + "Xóa" wrapped with `isAdmin` | ✅ PASS |
| Frontend shows 403 toast | `App.tsx` listens for `auth:forbidden` event | ✅ PASS |

## Evidence Log

### 2026-07-13 — Initial validation

**Commands executed:**
```
.venv/Scripts/python.exe -m pytest tests/test_auth.py tests/test_auth_api.py -v
  → 37/37 PASSED

.venv/Scripts/python.exe -m pytest tests/ -v
  → 211/211 PASSED

.venv/Scripts/python.exe scripts/validate_auth_roles.py
  → 15/15 PASSED
```

**Code changes verified:**
- `app/main.py:885` — `POST /api/persons/register`: `require_staff` → `require_admin` ✅
- `app/main.py:1088` — `PUT /api/persons/{id}`: `require_staff` → `require_admin` ✅
- `RegistryPage.tsx:306` — "Sửa" button wrapped with `isAdmin` ✅
- `RegistryPage.tsx:307` — "Xóa" button wrapped with `isAdmin` ✅
- `AdminPage.tsx:73` — "Người dùng" tab filtered by `isAdmin` ✅
- `AdminPage.tsx:152` — cleanup endpoint: `/api/admin/retention/cleanup` → `/api/admin/retention/run` ✅
- `AdminPage.tsx:317` — action column hidden for non-admin ✅
- `App.tsx:45` — 403 toast listener ✅
- `useAuth.tsx:65` — dispatches `auth:forbidden` on 403 ✅
- `PersonalSettings.tsx` — password change form ✅
- `app/auth.py` — `require_staff`, `require_admin`, `require_user` all wired ✅
- Seed LIBRARIAN user in `_seed_admin_user()` ✅
