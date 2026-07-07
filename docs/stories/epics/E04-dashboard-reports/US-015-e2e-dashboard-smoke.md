# US-015 E2E Dashboard Smoke and Demo Runbook

## Status

implemented

## Lane

normal

## Product Contract

LibCounterAI must have a repeatable browser-level smoke test and a human demo
runbook so reviewers can prove the dashboard workflow without reverse
engineering local commands.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/ai-pipeline.md`
- `docs/product/data-model.md`
- `docs/DEMO_RUNBOOK.md`

## Acceptance Criteria

- [x] Add a Playwright E2E smoke test for the browser dashboard.
- [x] Cover monitor, registry, history, analytics, backend status, and CSV export.
- [x] Mock backend API responses in the browser test so it is deterministic and does not require camera hardware.
- [x] Add stable UI selectors for E2E without changing user-visible behavior.
- [x] Add a demo runbook with quick proof, browser smoke, and manual demo commands.
- [x] Register US-015 in the Harness matrix with E2E proof.

## Design Notes

- Commands: `npm --prefix surfaces/browser run test:e2e`.
- UI surfaces: browser dashboard tabs and CSV export.
- API: mocked FastAPI endpoints for `/api/health`, `/api/cameras`,
  `/api/persons`, `/api/sessions`, `/api/stats/occupancy`, and
  `/api/stats/hourly`.
- Domain rules: this story proves dashboard wiring and review reproducibility;
  it does not prove camera hardware, RTSP reachability, or AI model accuracy.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id US-015 --unit 0 --integration 1 --e2e 1 --platform 1`.

| Layer | Expected proof |
| --- | --- |
| Unit | N/A |
| Integration | Vite/TypeScript build still passes |
| E2E | Playwright dashboard smoke passes |
| Platform | Runs on Windows PowerShell from repo root |
| Release | `story verify US-015` and `story verify-all` pass |

## Harness Delta

- Added US-015 to the durable Harness story matrix.
- Added `docs/DEMO_RUNBOOK.md` as the current demo operator guide.

## Evidence

- 2026-07-06: `npm --prefix surfaces/browser run test:e2e` passed.
- 2026-07-06: `.\scripts\bin\harness-cli.exe story verify US-015` passed.
- 2026-07-06: `.\scripts\bin\harness-cli.exe story verify-all` passed with
  `15 stories verified: 15 passed, 0 failed, 0 skipped`.
