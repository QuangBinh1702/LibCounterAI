# Design

## Role Model

| Role | Person View | Person Edit/Delete | Retention | Audit Log | User Management | Password Change |
|------|------------|-------------------|-----------|-----------|----------------|----------------|
| ADMIN | Full | Full | Full | Full | Full | Own only |
| LIBRARIAN | Read-only | None | Run + view status | View only | None | Own only |

## Application Flow

### API Role Guard Matrix

Endpoint | Current Guard | New Guard
---------|--------------|----------
`POST /api/auth/register` | `require_admin` | `require_admin` (unchanged)
`GET /api/auth/users` | `require_admin` | `require_admin` (unchanged)
`PUT /api/auth/password` | _nonexistent_ | `require_user` (NEW)
`POST /api/auth/login` | none (public) | none (unchanged)
`GET /api/auth/me` | `require_user` | `require_user` (unchanged)
`GET /api/persons` | none | `require_user`
`POST /api/persons/register` | none | `require_admin`
`PUT /api/persons/{id}` | none | `require_admin`
`DELETE /api/persons/{id}` | `require_admin` | `require_admin` (unchanged)
`GET /api/persons/{id}` | none | `require_user`
`POST /api/admin/retention/run` | `require_admin` | `require_staff`
`GET /api/admin/retention/config` | `require_admin` | `require_staff`
`GET /api/admin/retention/status` | `require_admin` | `require_staff`
`GET /api/admin/audit-log` | `require_admin` | `require_staff`
`GET /api/cameras` | none | `require_user`
`GET /api/events` | none | `require_user`
`GET /api/sessions` | none | `require_user`
`GET /api/analytics/*` | none | `require_user`
`POST /api/export/*` | none | `require_user`

### Password Change Flow

```
PUT /api/auth/password
Authorization: Bearer <token>
Body: { "current_password": "...", "new_password": "..." }
Response: 200 { "message": "Password updated" }
Errors: 400 if current password wrong, 422 if new password < 6 chars
```

The endpoint verifies `current_password` against the stored hash, then updates to `new_password`. The user can only change their own password — no admin override (out of scope).

### Frontend Role-Based Rendering

- `useAuth()` exposes `isAdmin` and new `isStaff` (or `role` directly).
- RegistryPage: LIBRARIAN cannot see "Đăng ký" button, edit/delete buttons on rows.
- AdminPage: LIBRARIAN sees only "Nhật ký" and "Lưu trữ" tabs, not "Người dùng".
- `apiFetch` in `useAuth.tsx`: on 401 → auto-logout; on 403 → show toast "Bạn không có quyền thực hiện thao tác này".

### User Management (AdminPage "Người dùng" enhancements)

Current: create user form only.

Additions:
- Toggle user status (ACTIVE ↔ INACTIVE) with confirmation dialog.
- Change user role (LIBRARIAN ↔ ADMIN) with confirmation.
- Refresh user list after any mutation.

New API:
```
PUT /api/auth/users/{id}
Authorization: Bearer <token> (require_admin)
Body: { "status": "INACTIVE" } or { "role": "LIBRARIAN" }
Response: 200 { "id": ..., "username": ..., "role": ..., "status": ... }
```

## Interface Contract

### `PUT /api/auth/password`

```
Request:  { "current_password": "...", "new_password": "..." }
Response: { "message": "Password updated" }
Errors:
  400 - "Current password is incorrect"
  422 - "New password must be at least 6 characters"
```

### `PUT /api/auth/users/{id}`

```
Request:  { "status": "INACTIVE" } | { "role": "LIBRARIAN" }
Response: { "id": 1, "username": "admin", "role": "LIBRARIAN", "status": "ACTIVE" }
Errors:
  400 - "Cannot deactivate the last ADMIN"
  403 - "Not authorized"
  404 - "User not found"
```

## Data Model

No schema changes. Existing `users` table with `role` and `status` columns is sufficient.

## UI / Platform Impact

- `AdminPage.tsx`: conditionally show "Người dùng" tab based on `isAdmin`; add user status/role mutation UI.
- `RegistryPage.tsx`: hide write actions for non-admin.
- `useAuth.tsx`: add 403 interceptor to `apiFetch`.
- `App.tsx`: expose role info if needed.
- `PersonalSettings.tsx`: add password change form (new section).
