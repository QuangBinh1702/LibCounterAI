# Design

## Domain Model

### New Entity: `audit_log`

| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PK | |
| `actor_type` | VARCHAR(20) | `'SYSTEM'`, `'STAFF'` |
| `actor_id` | INT | nullable — user ID for staff, NULL for system |
| `action` | VARCHAR(50) | e.g. `'RETENTION_PURGE'`, `'PERSON_DEACTIVATE'`, `'TEMPLATE_DELETE'` |
| `target_type` | VARCHAR(50) | e.g. `'events'`, `'visit_sessions'`, `'unknown_identities'`, `'face_templates'`, `'persons'` |
| `target_id` | INT | nullable |
|| `detail` | JSON | structured context — e.g. `{"rows_purged": 42, "retention_days": 90}` (uses `sqlalchemy.JSON` for cross-db SQLite/PostgreSQL compatibility) |
| `created_at` | TIMESTAMPTZ | |

### Modified Entity: `unknown_identities`

No schema change. The existing `expire_at` + `status` (`'ACTIVE'` / `'EXPIRED'`) is sufficient. Retention job sets `status = 'EXPIRED'` for rows past `expire_at`. Separate purge phase deletes expired rows older than a configurable grace period.

### Modified Entity: `face_templates`

No schema change. When a person's status changes to `'INACTIVE'`, a configurable grace period starts. After the grace period, templates are hard-deleted from the database. The existing `is_active = FALSE` is used as a soft-disable flag for re-enrollment, not for lifecycle purging.

### Retention Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `RETENTION_EVENT_DAYS` | 365 | Purge events older than N days |
| `RETENTION_SESSION_DAYS` | 365 | Purge closed/session rows older than N days |
| `RETENTION_UNKNOWN_EXPIRE_DAYS` | 7 | Max days before unknown identity auto-expires (mirrors current `expire_at` logic) |
| `RETENTION_UNKNOWN_PURGE_DAYS` | 30 | Delete expired unknown identity rows after N days |
| `RETENTION_TEMPLATE_GRACE_DAYS` | 90 | Days after person deactivation before templates are purged |
| `RETENTION_AUDIT_LOG_DAYS` | 730 | Purge audit log rows older than N days |

## Application Flow

### Retention Job (CLI command + API trigger)

```
scripts\run_retention.py  [--dry-run] [--age-days N]
POST /api/admin/retention/run  {"dry_run": true}
GET  /api/admin/retention/status
```

Flow:
1. Read retention config from env vars.
1. Read retention config from env vars.
2. Phase 1 — Timeout stale sessions: `UPDATE visit_sessions SET status = 'TIMEOUT', updated_at = NOW() WHERE status = 'ACTIVE' AND entry_at < NOW() - INTERVAL 'RETENTION_SESSION_DAYS days'`.
3. Phase 2 — Expire unknown identities: `UPDATE unknown_identities SET status = 'EXPIRED' WHERE status = 'ACTIVE' AND expire_at < NOW()`.
4. Phase 3 — Purge events older than `RETENTION_EVENT_DAYS`.
5. Phase 4 — Purge visit_sessions (CLOSED, TIMEOUT, UNMATCHED) older than `RETENTION_SESSION_DAYS`.
6. Phase 5 — Purge face_templates where `is_active = FALSE` and `created_at < NOW() - INTERVAL 'RETENTION_TEMPLATE_GRACE_DAYS days'`.
7. Phase 6 — Delete expired unknown identity rows where `status = 'EXPIRED'` and `expire_at < NOW() - INTERVAL 'RETENTION_UNKNOWN_PURGE_DAYS days'`.
8. Phase 7 — Purge audit log rows older than `RETENTION_AUDIT_LOG_DAYS` (must be last — all earlier phases write audit entries during this run).
9. Each phase is wrapped in its own transaction. If a phase crashes, earlier phases are committed and later phases are skipped.
10. Each phase writes a row to `audit_log` with counts (including skipped/crashed phases write an error entry).
11. `--dry-run` logs planned actions without executing deletes, using a single rollback transaction.

### Staff Deactivation Flow

When a staff user sets `persons.status = 'INACTIVE'`:
- The API handler writes an audit log entry.
- The retention job will purge templates after `RETENTION_TEMPLATE_GRACE_DAYS` — the grace period gives the operator a window to reactivate without data loss.

## Interface Contract

### `POST /api/admin/retention/run`

Request:
```json
{"dry_run": false}
```

Response:
```json
{
  "phases": [
    {"phase": "timeout_stale_sessions", "rows_affected": 2, "dry_run": false},
    {"phase": "expire_unknowns", "rows_affected": 5, "dry_run": false},
    {"phase": "purge_events", "rows_affected": 300, "dry_run": false},
    {"phase": "purge_sessions", "rows_affected": 50, "dry_run": false},
    {"phase": "purge_templates", "rows_affected": 0, "dry_run": false},
    {"phase": "purge_expired_unknowns", "rows_affected": 3, "dry_run": false},
    {"phase": "purge_audit_log", "rows_affected": 120, "dry_run": false}
  ]
  "duration_ms": 452
}
```

### `GET /api/admin/retention/status`

Response:
```json
{
  "config": {
    "event_days": 365,
    "session_days": 365,
    "unknown_expire_days": 7,
    "unknown_purge_days": 30,
    "template_grace_days": 90,
    "audit_log_days": 730
  },
  "counts": {
    "active_unknowns": 12,
    "expired_unknowns_pending_purge": 3,
    "events_older_than_retention": 180,
    "sessions_older_than_retention": 22,
    "inactive_templates_pending_purge": 0,
    "audit_log_rows": 50
  }
}
```

Errors: `401` if no auth (future concern — currently no auth, so endpoint is open but documented as admin-only).

## Data Model

### New Migration

- `audit_log` table (as described above). `detail` uses `sqlalchemy.JSON` for cross-db SQLite/PostgreSQL compatibility.
- Index on `audit_log(action, created_at)`.
- Index on `audit_log(actor_type, actor_id)`.

### Modified Behavior (no schema change)

- `unknown_identities`: enforce expire via retention job.
- `face_templates`: enforce purge via retention job.

## UI / Platform Impact

- No new UI in this story — retention is env-var + API driven.
- Python script at `scripts/run_retention.py` for CLI invocation.
- Two new routes in `app/main.py` (admin-only, no auth gate yet).
- New model + migration in `app/models.py` and `app/alembic/`.

## Observability

- Every retention run writes one `audit_log` row per phase.
- Retention status endpoint provides point-in-time read.
- Future: could emit metrics, but not in scope for this story.

## Alternatives Considered

1. **Retention as a background thread/scheduler** — rejected for this iteration because the app has no scheduler dependency. CLI + API-triggered keeps things simple; a Windows scheduled task or cron wrapper can be added later.
2. **Hard-delete only, no audit log** — rejected because audit trail is a hard requirement for production readiness.
3. **Anonymize instead of purge** — rejected for v1. Purging is simpler and the data model doesn't use anonymization tokens. Can revisit if compliance requirements emerge.
