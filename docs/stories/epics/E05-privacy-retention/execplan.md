# Exec Plan

## Goal

Ship a working retention system that enforces data lifecycle policies for events, sessions, unknown identities, face templates, and audit logging, with a durable audit trail and on-demand execution.

## Scope

In scope:
- `audit_log` table + Alembic migration.
- `app/retention.py` — retention engine with dry-run and per-phase transaction support.
- `scripts/run_retention.py` — CLI wrapper around `app/retention.py`.
- `POST /api/admin/retention/run` and `GET /api/admin/retention/status` endpoints.
- Environment variable configuration for all retention periods.
- Retention phases: expire unknowns, purge events/sessions, purge inactive templates, purge audit log, purge expired unknown rows.
- Seeding a few audit log rows in demo seed data to prove the table works.
- Validation script: `scripts/validate_retention.py`.

Out of scope:
- UI for retention settings or manual trigger (API-only).
- Scheduled/cron integration (document how to wire it, but don't ship a scheduler).
- Auth gate on admin endpoints (same as all other endpoints today — documented as admin-only).
- Anonymization strategies beyond purging.

## Risk Classification

Risk flags:
- Data model: new `audit_log` table, new migration.
- Audit/security: audit logging and data lifecycle are security-sensitive.
- Existing behavior: changes `unknown_identities` enforcement from theoretical to actual.
- Weak proof: retention area has no existing tests.
- Multi-domain: backend models, API, migration, CLI script, environment config.

Hard gates:
- Data loss or migration: retention purges delete production data.
- Audit/security: audit logging governs data lifecycle compliance.

## Work Phases

1. **Migration and model**: Add `AuditLog` model to `app/models.py`, generate Alembic migration.
2. **Retention engine**: Implement `app/retention.py` with all 7 phases, dry-run support, per-phase transactions, and audit log writes.
3. **CLI wrapper**: `scripts/run_retention.py` — thin CLI around `app/retention.py`.
4. **API endpoints**: Add `POST /api/admin/retention/run` and `GET /api/admin/retention/status` to `app/main.py`.
5. **Validation**: Write `scripts/validate_retention.py` that seeds test data, runs retention, and checks counts.
6. **Demo seed update**: Add a few `audit_log` rows to `scripts/setup_database.py --seed-demo` for dashboard proof.
7. **Docs update**: Update `docs/product/data-model.md`, `docs/product/overview.md`, and `docs/ARCHITECTURE.md` security notes.
8. **Harness update**: Register story, update matrix, add `story verify` command.
9. **Proof**: Run validation against both SQLite and PostgreSQL.

## Stop Conditions

Pause for human confirmation if:
- Any phase proposes `DELETE` without a corresponding `audit_log` write.
- Environment variable names or default values need to change from the design.
- Migration strategy needs to handle existing production data differently.
- Validation requirements need to be weakened.
