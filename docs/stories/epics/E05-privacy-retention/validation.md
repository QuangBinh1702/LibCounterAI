# Validation

## Proof Strategy

The story is proven when `scripts/validate_retention.py` passes against both SQLite (fast dev loop) and PostgreSQL (product-aligned). The validation script seeds synthetic rows with known timestamps, runs retention with `--dry-run` and without, and asserts correct row counts before and after. Additionally, the demo seed includes audit log rows and the retention status endpoint returns the expected structure.

## Test Plan

| Layer | Cases |
|-------|-------|
| Unit | `app/retention.py` phase functions tested with in-memory SQLite |
| Integration | `scripts/validate_retention.py` seeds data, runs retention, checks DB counts |
| E2E | N/A — no UI for this story |
| Platform | Runs on Windows PowerShell from repo root using the project venv, against both SQLite and PostgreSQL |
| Performance | Measure `POST /api/admin/retention/run` with 10k event rows — must complete under 5s |
| Logs/Audit | Verify audit_log rows are created for each retention phase with correct detail JSON |

## Fixtures

- Deterministic test data: 10 events older than retention window, 5 events younger, 3 expired unknown identities, 2 active, 1 deactivated person with inactive templates, 40 audit log rows >730 days old, 10 audit log rows <730 days old, 2 ACTIVE sessions older than retention window, 3 CLOSED sessions younger than retention window.
- All timestamps are anchored to known dates so retention calculations are deterministic.

## Commands

```text
.\.venv\Scripts\python.exe scripts\validate_retention.py
.\.venv\Scripts\python.exe scripts\validate_retention.py --require-postgres
```

## Acceptance Evidence

| Check | Method |
|-------|--------|
| `timeout_stale_sessions` marks ACTIVE sessions past retention as TIMEOUT | Run retention, query `visit_sessions` |
| `timeout_stale_sessions` does not touch sessions before threshold | Same query |
| `expire_unknowns` marks ACTIVE rows past `expire_at` as EXPIRED | Run retention, query `unknown_identities` |
| `expire_unknowns` does not touch rows before `expire_at` | Same query |
| `purge_events` deletes events older than `RETENTION_EVENT_DAYS` | Count events before/after |
| `purge_sessions` deletes sessions (CLOSED/TIMEOUT/UNMATCHED) older than `RETENTION_SESSION_DAYS` | Count sessions before/after |
| `purge_templates` deletes inactive templates older than `RETENTION_TEMPLATE_GRACE_DAYS` | Count templates before/after |
| `purge_audit_log` deletes audit rows older than `RETENTION_AUDIT_LOG_DAYS` | Count audit_log before/after |
| `purge_expired_unknowns` deletes expired rows older than `RETENTION_UNKNOWN_PURGE_DAYS` | Count unknowns before/after |
| `--dry-run` returns same counts but makes no deletes | Compare dry-run vs real: counts match, rows unchanged |
| Each phase writes an audit_log row | Query audit_log after run |
| `GET /api/admin/retention/status` returns expected config + counts | Call endpoint, assert structure |
| `POST /api/admin/retention/run` returns structured phase results | Call endpoint, assert phase array |
| Double run is idempotent | Run twice; second run reports 0 rows affected |
| Run against empty database — no errors, 0 rows affected all phases | Run retention on fresh DB |
