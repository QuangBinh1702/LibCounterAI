# US-016 Demo Seed Data

## Status

implemented

## Lane

normal

## Product Contract

LibCounterAI must provide repeatable seed data for a real-backend manual demo
so reviewers can open the dashboard and immediately see cameras, known persons,
unknown visitors, visit sessions, occupancy, and hourly analytics without
manually creating records.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/data-model.md`
- `docs/DEMO_RUNBOOK.md`

## Acceptance Criteria

- [x] Extend `scripts/setup_database.py --seed-demo` beyond a camera-only seed.
- [x] Seed one demo camera and camera config.
- [x] Seed two known persons with active 128-dimensional SFace templates.
- [x] Seed one active unknown identity.
- [x] Seed deterministic ENTRY/EXIT events and visit sessions for dashboard history and analytics.
- [x] Keep seed behavior idempotent so repeated runs refresh demo data instead of duplicating it.
- [x] Add validation that checks database rows and API-readable dashboard data.

## Design Notes

- Commands: `.\.venv\Scripts\python.exe scripts\setup_database.py --require-postgres --seed-demo`.
- Verification: `.\.venv\Scripts\python.exe scripts\validate_demo_seed.py`.
- Tables: `cameras`, `camera_configs`, `persons`, `face_templates`,
  `unknown_identities`, `events`, `visit_sessions`.
- Domain rules: the demo seed uses synthetic embedding vectors and deterministic
  demo identifiers. It is for local demonstration, not biometric enrollment
  quality proof.
- UI surfaces: monitor backend status, member registry, visit history, CSV
  export, occupancy cards, and hourly analytics can all render populated data.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-016 --unit 0 --integration 1 --e2e 0 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | `scripts/validate_demo_seed.py` runs seed twice against the configured `.env` database, checks DB counts, and reads dashboard APIs |
| E2E | N/A; browser smoke remains covered by US-015 |
| Platform | Runs on Windows PowerShell from repo root using the project venv |
| Release | `story verify US-016` and `story verify-all` pass |

## Harness Delta

- Added US-016 to the durable Harness story matrix.
- Updated the demo runbook to describe full demo seed data.
- Removed demo seed data from recommended next stories.

## Evidence

- 2026-07-07: `.\.venv\Scripts\python.exe scripts\validate_demo_seed.py` passed.
- 2026-07-07: `.\.venv\Scripts\python.exe scripts\setup_database.py --require-postgres --seed-demo` used repo `.env`, connected to PostgreSQL, created pgvector extension/indexes, and seeded demo data.
- 2026-07-07: `.\.venv\Scripts\python.exe scripts\validate_demo_seed.py` passed against PostgreSQL/pgvector via repo `.env`.
