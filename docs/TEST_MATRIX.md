# Test Matrix

This file maps product behavior to proof.

The durable source of truth for proof status is the Harness database:

```powershell
.\scripts\bin\harness-cli.exe query matrix
```

This markdown file mirrors the current high-level state for quick review. Keep
it synchronized when story proof changes.

## Status Values

| Status | Meaning |
| --- | --- |
| planned | Accepted as intended behavior, not implemented |
| in_progress | Actively being built |
| implemented | Implemented and proof exists |
| changed | Contract changed after earlier implementation |
| retired | No longer part of the product contract |

## Matrix

| Story | Contract | Unit | Integration | E2E | Platform | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US-001 | Project structure setup and health check verification | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-002 | Basic person detection and tracking using YOLO and ByteTrack | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-003 | Database models and schema setup | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-004 | Virtual line and line crossing detection | yes | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-005 | Interactive web UI for real-time detection and counting | no | yes | no | yes | implemented | `npm --prefix surfaces/browser run lint`, `npm --prefix surfaces/browser run build`, `harness-cli story verify US-005` passed on 2026-07-06 |
| US-006 | Face detection and embedding extraction pipeline | yes | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-007 | Known person registration enrollment API | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-008 | Real-time face matching and event logging | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-009 | RTSP camera connection and testing API | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-010 | Unknown re-identification and storage | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-011 | Unknown visit session tracking | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-012 | Unknown session API and UI sync | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-013 | CSV export and date-filtered sessions | no | yes | no | yes | implemented | Story packet proof; Harness matrix |
| US-014 | Enhanced analytics with known-unknown breakdown | no | yes | no | yes | implemented | Story packet proof; Vietnam UTC+7 hourly aggregation and chart contract documented; timezone smoke proof passed |
| US-015 | E2E dashboard smoke and demo runbook | no | yes | yes | yes | implemented | `npm --prefix surfaces/browser run test:e2e` passed on 2026-07-06 |
| US-016 | Demo seed data for real-backend dashboard demo | no | yes | no | yes | implemented | `.\.venv\Scripts\python.exe scripts\validate_demo_seed.py` passed against PostgreSQL/pgvector via repo `.env` on 2026-07-07 |
| US-017 | One-command local dev stack | no | no | no | yes | implemented | `validate_dev_stack.ps1 -NoInstall` passed on 2026-07-13: backend healthy, frontend HTTP 200, 4 seeded sessions |
| E05 | Privacy and retention hardening | no | yes | no | yes | implemented | `DATABASE_URL=sqlite:///./test_retention.db .venv/Scripts/python.exe scripts/validate_retention.py` passes 16 checks; `pytest tests/` 170/170 pass; `python scripts/validate_retention.py` (default PostgreSQL) passes 16 checks on 2026-07-13 |

## Evidence Rules

- Unit proof covers pure domain and application rules.
- Integration proof covers backend enforcement, data integrity, provider
  behavior, jobs, or service contracts.
- E2E proof covers user-visible browser flows.
- Platform proof covers only shell, deployment, mobile, desktop, or runtime
  behavior that cannot be proven in lower layers.
- A story can be implemented without every proof column if the story packet
  explains why.

## Current Gaps

- Most implemented stories still lack unit-level proof.
- US-015 records browser E2E smoke proof for the dashboard workflow.
- US-016 records repeatable real-backend demo seed proof for camera, persons,
  sessions, and analytics data.
- US-017 platform proof: `validate_dev_stack.ps1 -NoInstall` passes with Docker Desktop running and fresh PG17 volumes.
- `.\scripts\bin\harness-cli.exe story verify-all` passed for all 16 stories on 2026-07-07; US-017 fixed and proven on 2026-07-13 (now 17 implemented).
- E05 Privacy and retention hardening added on 2026-07-13: `app/retention.py` engine, 7 phases, dry-run, audit logging, CLI + API, SQLite proof passes 16 checks, 170/170 backend tests pass; PostgreSQL proof passes 16 checks on 2026-07-13 (`validate_retention.py` default Postgres).
