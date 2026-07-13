# Exec Plan

## Goal

Ship role-based access control (ADMIN / LIBRARIAN) that restricts person write operations, exposes retention/audit to LIBRARIAN, hides admin-only UI sections, and adds password change + user management.

## Scope

In scope:
- `app/auth.py` — wire `require_staff` to retention and audit endpoints.
- `app/main.py` — add role guards to all endpoints per design matrix; add `PUT /api/auth/password`; add `PUT /api/auth/users/{id}`.
- `surfaces/browser/src/hooks/useAuth.tsx` — 403 interceptor in `apiFetch`.
- `surfaces/browser/src/components/RegistryPage.tsx` — hide write actions for non-admin.
- `surfaces/browser/src/components/AdminPage.tsx` — hide "Người dùng" tab for non-admin; add user status/role mutation UI.
- `surfaces/browser/src/components/PersonalSettings.tsx` — add password change section.
- `scripts/setup_database.py` — seed one LIBRARIAN user.
- `tests/test_auth.py` — update for new endpoints and role checks.
- Story packet + validation script.

Out of scope:
- OAuth/SSO, API keys, custom roles, rate limiting.

## Risk Classification

Risk flags:
- Existing behavior: changing endpoint guards may break existing clients (no known clients beyond the bundled UI).
- Multi-domain: backend API, frontend components, auth hook, tests.

## Work Phases

1. **Backend role guards**: Add `require_user` / `require_admin` / `require_staff` to all endpoints per design matrix. Wire `require_staff` to retention and audit endpoints.
2. **Password change endpoint**: `PUT /api/auth/password`.
3. **User management endpoint**: `PUT /api/auth/users/{id}` for status/role mutation.
4. **Frontend 403 interceptor**: Add toast + redirect logic to `apiFetch`.
5. **RegistryPage role hiding**: Conditionally show/hide write buttons.
6. **AdminPage enhancements**: Hide "Người dùng" tab for non-admin; add status toggle + role change UI.
7. **PersonalSettings password form**: Add password change section.
8. **Demo seed**: Add LIBRARIAN user.
9. **Tests**: Update `test_auth.py`, add validation script.
10. **Harness update**: Register story, update matrix.

## Stop Conditions

Pause for human confirmation if:
- An existing endpoint's role guard changes from open to restricted — may affect demo workflows.
- Password change endpoint design needs to differ from spec.
- Frontend role check can be bypassed via direct API calls (it can — backend is the real gate).
