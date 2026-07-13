# US-021 Role-Based Access Control (ADMIN / LIBRARIAN)

## Status

implemented

## Lane

high-risk

## Product Contract

Staff roles (ADMIN / LIBRARIAN) restrict person write operations, expose retention/audit to LIBRARIAN, hide admin-only UI sections, and support password change + user management.

## Relevant Product Docs

- `docs/ARCHITECTURE.md` (security notes)
- `docs/product/data-model.md`
- `docs/stories/epics/E06-auth-roles/overview.md`
- `docs/stories/epics/E06-auth-roles/design.md`
- `docs/stories/epics/E06-auth-roles/execplan.md`

## Acceptance Criteria

1. LIBRARIAN can log in, view registry (no edit/delete), run retention, view audit log, but cannot access user management or create/update persons.
2. ADMIN has full access to everything.
3. `PUT /api/auth/password` works for any authenticated user.
4. `PUT /api/auth/users/{id}` allows ADMIN to toggle status/role; LIBRARIAN gets 403.
5. Backend 403 responses show toast "Bạn không có quyền thực hiện thao tác này" on frontend.
6. `scripts/validate_auth_roles.py` passes all 15 checks.
7. `pytest tests/test_auth.py tests/test_auth_api.py` passes all 37 auth tests.

## Design Notes

- Commands: `PUT /api/auth/password`, `PUT /api/auth/users/{id}`
- Queries: `GET /api/auth/me`, `GET /api/auth/users`, `GET /api/admin/audit-log`, `GET /api/admin/retention/config`, `GET /api/admin/retention/status`
- API: `require_user` on person/event/session/camera reads; `require_admin` on person/register, person update, person delete, user management, camera create/update/delete; `require_staff` on retention run/config/status and audit-log
- Tables: existing `users` table with `role` (ADMIN/LIBRARIAN) and `status` (ACTIVE/INACTIVE) — no schema changes
- Domain rules: last ADMIN cannot be deactivated; LIBRARIAN is read-only on persons
- UI surfaces: RegistryPage hides edit/delete for non-admin; AdminPage hides "Người dùng" tab for non-admin; PersonalSettings adds password change form

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `test_auth.py` — hash/verify/JWT/require_user/admin/staff (18 tests) |
| Integration | `test_auth_api.py` — login, register, auth-me, password-change, user-list, person-role-guard, retention-staff-access (19 tests) |
| E2E | `validate_auth_roles.py` — 15 role-based checks covering all acceptance criteria |
| Platform | Browser 403 toast via `auth:forbidden` event in `App.tsx` |

## Harness Delta

- Created `US-E06-ROLE-FIX` story in harness matrix (gap fixes)
- Created `US-021` story in harness matrix (full auth roles)
- Created `scripts/validate_auth_roles.py` for automated proof
- Updated `docs/stories/backlog.md` with E06 status

## Evidence

### 2026-07-13: Full Auth Roles Validation

**pytest (37 auth tests):**
```
tests/test_auth.py:: 18/18 PASSED
tests/test_auth_api.py:: 19/19 PASSED
```

**Full test suite (211 tests):**
```
pytest tests/ — 211/211 PASSED
```

**Validation script (15/15 checks PASSED):**
```
PASS: LIBRARIAN can view registry (GET /api/persons)
PASS: LIBRARIAN cannot create person (POST /api/persons/register)
PASS: LIBRARIAN cannot delete person (DELETE /api/persons/1)
PASS: LIBRARIAN can run retention (POST /api/admin/retention/run)
PASS: LIBRARIAN can view audit log (GET /api/admin/audit-log)
PASS: LIBRARIAN cannot list users (GET /api/auth/users)
PASS: LIBRARIAN cannot create user (POST /api/auth/register)
PASS: ADMIN can view registry
PASS: ADMIN can list users
PASS: ADMIN can run retention
PASS: ADMIN can view audit log
PASS: Password change succeeds with correct password
PASS: Password change fails with wrong password
PASS: Admin can toggle user status
PASS: Admin can change user role
```

**Frontend 403 toast:** `App.tsx:45` listens for `auth:forbidden` custom event dispatched by `useAuth.tsx:65` on API 403 responses; shows toast "Bạn không có quyền thực hiện thao tác này."

**RegistryPage role hiding:** `RegistryPage.tsx:306-307` both "Sửa" and "Xóa" buttons wrapped with `{isAdmin && ...}` — LIBRARIAN sees no write actions.

**AdminPage tab filtering:** `AdminPage.tsx:73` filters out "Người dùng" tab when `!isAdmin`. `AdminPage.tsx:317` hides action column for non-admin.
