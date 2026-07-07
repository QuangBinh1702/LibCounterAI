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
15 stories verified: 15 passed, 0 failed, 0 skipped
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

For a manual demo with the real backend:

```powershell
docker compose up -d db redis
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:POSTGRES_DB="libcounterai"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="password"
$env:REDIS_HOST="localhost"
$env:REDIS_PORT="6379"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app\requirements.txt
.\.venv\Scripts\python.exe scripts\setup_database.py --require-postgres --seed-demo
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir app --host 127.0.0.1 --port 8000
```

The production-aligned database is PostgreSQL with pgvector. The setup script
creates the `vector` extension, creates SQLAlchemy tables, and adds HNSW vector
indexes for known and unknown face embeddings.

In a second terminal:

```powershell
npm --prefix surfaces/browser install
npm --prefix surfaces/browser run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

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
