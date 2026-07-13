# Overview

## Current Behavior

- JWT auth with `require_admin`/`require_staff`/`require_user` dependencies exist but are inconsistently applied.
- `require_staff` (ADMIN + LIBRARIAN) is defined in `app/auth.py` but **never used** on any endpoint.
- `require_admin` is used on: register, user list, retention, audit log, person delete.
- Most person/event/session/view endpoints have **no role check** — any authenticated user can delete, edit, export data.
- Frontend exposes "Admin" tab only to ADMIN role, but `apiFetch` has no 403/401 interceptor — errors are silent.
- LIBRARIAN role sees identical UI to ADMIN (minus the Admin tab).
- No password change endpoint exists.
- No user management UI beyond user creation form in AdminPage (no activate/deactivate, no role change).

## Target Behavior

- LIBRARIAN: read-only access to person registry, can run retention and view audit log, cannot delete persons or manage users.
- ADMIN: full access to everything including user management, person deletion, role assignment.
- Person write endpoints (create, update, delete) gated by `require_admin`.
- Registry view on frontend hides edit/delete buttons for LIBRARIAN.
- `POST /api/auth/password` for any authenticated user to change own password.
- AdminPage gets user management: toggle active/inactive, change role.
- `apiFetch` interceptor shows toast on 403 and redirects to login on 401.
- Demo seed includes one LIBRARIAN user.

## Affected Users

- Librarians: can view data, run retention, view audit log — cannot delete persons or manage users.
- Admins: full control.
- Library members: protected from accidental deletion by non-admin staff.

## Affected Product Docs

- `docs/ARCHITECTURE.md` (security notes)
- `docs/product/data-model.md`

## Non-Goals

- No OAuth/SSO integration.
- No permission matrix or custom roles beyond ADMIN/LIBRARIAN.
- No API key authentication for external integrations.
- No rate limiting or brute-force protection (separate concern).
