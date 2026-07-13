# US-017 One-Command Local Dev Stack

## Status

implemented

## Story

As a developer preparing a real-backend demo, I can run one PowerShell command
that starts PostgreSQL, Redis, FastAPI, and the browser dashboard with demo
data loaded.

## Acceptance Criteria

- `npm run dev` starts FastAPI and Vite in the foreground through `concurrently`
  with `[api]` / `[web]` log prefixes while Docker PostgreSQL/Redis are managed
  separately.
- `npm run dev:api` and `npm run dev:web` start only that side.
- `npm run prepare:dev` / `npm run dev:full` start Docker PostgreSQL and Redis
  through the PowerShell prepare script without requiring a machine-wide
  execution policy change.
- The prepare script creates the Python virtual environment when needed.
- The prepare script installs Python and browser dependencies unless
  `-NoInstall` is supplied.
- The prepare script prepares PostgreSQL schema and deterministic demo seed data
  unless `-NoSeed` is supplied.
- App processes stream logs in the terminal; `Ctrl+C` stops both sides.

## Scope

- In scope: local Windows/PowerShell developer workflow for real-backend demo
  startup and shutdown.
- Out of scope: production deployment orchestration and containerizing the AI
  camera runtime.

## Proof

- Integration target: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\validate_dev_stack.ps1 -NoInstall`
- Platform target: the validation starts Docker services, FastAPI, and Vite,
  checks backend health, checks seeded sessions through the API, checks the
  browser dashboard HTTP response, then stops background app processes.

2026-07-13: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\validate_dev_stack.ps1 -NoInstall` passed:
backend healthy, frontend HTTP 200, 4 seeded sessions returned via API.

## Delta

- Added root `package.json` with `concurrently` so `npm run dev` mirrors a
  typical Vite + API monorepo (`dev:api` / `dev:web`).
- Added `scripts/run-dev-api.mjs` and `scripts/run-dev-web.mjs` to honor `.env`
  ports while streaming logs in the foreground.
- Kept `scripts/dev.ps1` / `scripts/dev.cmd` for Docker/venv/seed prepare only.
- Added `scripts/validate_dev_stack.ps1` so Harness can prove prepare + concurrent
  startup without leaving FastAPI and Vite running.
- Updated the demo runbook with the new preferred workflow.
- 2026-07-13: Fixed `Test-DockerReady` in `dev.ps1` to use `docker ps` instead of `docker info` (PowerShell `*>` redirection caused `docker info` to receive `*` as an argument).
- 2026-07-13: Fixed `validate_dev_stack.ps1` — sessions API date changes from hardcoded `2026-07-07` to today's date; frontend URL changed from `127.0.0.1` to `localhost` (Vite binds to IPv6 only; `localhost` resolves to `[::1]` on Windows).
