# LibCounterAI Demo Runbook

Use this runbook to prove the current demo build from a clean checkout.

## Prerequisites

- Python environment with `app/requirements.txt` installed.
- Node dependencies installed under `surfaces/browser/`.
- Playwright Chromium installed for browser smoke tests:

```powershell
npm --prefix surfaces/browser run test:e2e
```

If Playwright reports a missing browser, install Chromium once:

```powershell
npm --prefix surfaces/browser exec playwright install chromium
```

## Quick Proof

Run the full Harness verification suite:

```powershell
.\scripts\bin\harness-cli.exe story verify-all
```

Expected result:

```text
16 stories verified: 16 passed, 0 failed, 0 skipped
```

## Browser Smoke

Run the dashboard E2E smoke test:

```powershell
npm --prefix surfaces/browser run test:e2e
```

This starts Vite on `http://127.0.0.1:4174`, mocks the FastAPI endpoints used by
the dashboard, opens Chromium, and checks:

- monitor tab renders and backend status becomes online;
- registry tab renders known person data;
- history tab renders an unknown visitor session;
- CSV export produces a file;
- analytics tab renders occupancy cards.

## Manual Demo

For a manual demo with the real backend, use the one-command local dev launcher:

```powershell
npm run dev
```

This uses `concurrently` in the foreground with colored `[api]` / `[web]`
prefixes, the same pattern as a typical Vite + API monorepo. Logs stream in the
terminal; press `Ctrl+C` to stop both processes. Docker PostgreSQL and Redis are
expected to be managed separately for the default command.

Start only one side when needed:

```powershell
npm run dev:api
npm run dev:web
```

Prepare Docker services and demo seed data, then start both apps:

```powershell
npm run prepare:dev
npm run dev
```

Or do both in one step:

```powershell
npm run dev:full
```

The backend reads local runtime settings from the repo-root `.env` file. The
production-aligned database is PostgreSQL with pgvector. The setup flow creates
the `vector` extension, creates SQLAlchemy tables, and adds HNSW vector indexes
for known and unknown face embeddings. It also refreshes deterministic demo
data:

- one `Demo Gate` camera and line configuration;
- two known people with active 128-dimensional SFace templates;
- one active unknown visitor identity;
- ENTRY/EXIT events and visit sessions that populate history, CSV export,
  occupancy, known/unknown breakdown, and hourly analytics.

The demo seed is idempotent. Running it again refreshes the demo records instead
of duplicating sessions or events.

Open the frontend URL printed by `npm run dev`. By default it follows
`FRONTEND_PORT` in `.env` (currently often `http://127.0.0.1:5175`). Press
`Ctrl+C` in that terminal to stop both processes.

Demo path:

1. Confirm the server indicator is online.
2. Open the monitor tab and choose webcam, upload, or RTSP source.
3. Draw or adjust the virtual line when a video source is visible.
4. Start analysis and watch entry/exit counters and event log.
5. Open the members tab to register or review known persons.
6. Open history to filter sessions and export CSV.
7. Open analytics to review occupancy, entries, exits, and hourly volume.

## Known Limits

- The automated browser smoke mocks API responses. It proves dashboard wiring,
  tab navigation, rendering, and CSV export, not camera hardware.
- Real camera/webcam validation still needs a manual run because local devices
  and RTSP endpoints vary by machine.
