# US-020 Member Update CRUD action on registry page

## Status

implemented

## Lane

normal

## Product Contract

Add an "Edit" (Sửa) button next to the "Delete" (Xóa) button on the members listing page. Clicking the edit button changes the registration form to edit/update mode (populating current member details: name, member code, role, status), with an option to select a new portrait image. Submitting the form updates the database. A "Cancel" (Hủy) button resets the form back to registration mode.

## Relevant Product Docs

- `README.md`
- `SPEC.md`

## Acceptance Criteria

- [x] Edit action is present on the members listing table.
- [x] Clicking Edit populates the form and flips the card into update mode.
- [x] Cancel button exits update mode and resets form.
- [x] PUT `/api/persons/{person_id}` endpoint updates person details and face template (if new file is uploaded).
- [x] Duplicate member codes are rejected during update (excluding self).
- [x] Form validation works and shows success toast on successful save.
- [x] Update dialog is rendered in a document-level portal so its backdrop covers the whole viewport, including the fixed header and animated page region.
- [x] Update dialog locks background scroll, focuses the name field, and closes via Escape or backdrop click.

## Design Notes

- **API**: `PUT /api/persons/{person_id}`
- **UI surfaces**: Member registration card & members list table in `App.tsx`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | verified manually |
| Integration | verified manually |
| E2E | verified manually |

## Harness Delta

N/A

## Evidence

Frontend Vite production build succeeded:
```bash
vite v8.1.3 building client environment for production...
built in 967ms
```

2026-07-10 visual polish: member-update dialog now uses a document-level portal
to preserve a full-viewport backdrop while page transitions are animated. The
browser unit suite passed: 9 files / 40 tests. The existing dashboard E2E smoke
currently stops at authentication before its monitor assertion and needs its
login fixture updated separately.
