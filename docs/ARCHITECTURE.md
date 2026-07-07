# Architecture

LibCounterAI is a FastAPI and React/Vite application for library visitor
counting, known-person enrollment, face matching, unknown visitor
re-identification, visit sessions, and dashboard reporting.

The reusable Harness remains in this repository, but the app is no longer an
empty Harness install. This document is the current architecture map for agent
work before changing code.

## Runtime Surfaces

| Surface | Path | Responsibility |
| --- | --- | --- |
| Backend API | `app/main.py` | FastAPI routes for health, frame processing, person enrollment, cameras, events, sessions, and analytics. |
| Persistence | `app/database.py`, `app/models.py`, `app/alembic/` | SQLAlchemy models, PostgreSQL/pgvector or SQLite development fallback, and Alembic migrations. |
| AI pipeline | `app/detector.py`, `app/tracker.py`, `app/face_pipeline.py` | YOLOv8 ONNX person detection, IoU tracking, line crossing, OpenCV YuNet face detection, and SFace embeddings. |
| Browser dashboard | `surfaces/browser/` | React/Vite dashboard for monitor, registry, visit history, CSV export, analytics, theme, and E2E smoke checks. |
| Local services | `docker-compose.yml` | PostgreSQL with pgvector and Redis for local product-aligned runtime. |
| Harness operations | `scripts/bin/harness-cli.exe`, `docs/stories/`, `harness.db` | Durable story status, verification commands, intake, traces, backlog, and decisions. |

## Stack Decisions

- Backend: Python FastAPI, SQLAlchemy, OpenCV, ONNX Runtime, pgvector.
- Frontend: React, TypeScript, Vite, Framer Motion, Phosphor Icons.
- Database: PostgreSQL with pgvector is the product-aligned target. SQLite is a
  development and validation fallback for scripts that do not require pgvector
  indexes.
- Cache/state substrate: Redis is part of the local service contract, but the
  current backend health endpoint only reports Redis configuration and does not
  actively use Redis for session state yet.
- AI models: ONNX model files live under `app/` and are runtime assets. Do not
  ignore or remove them unless a replacement startup download path is verified.

Durable stack decisions are recorded in:

- `docs/decisions/0008-frontend-stack.md`
- `docs/decisions/0009-backend-and-ai-stack.md`
- `docs/decisions/0010-database-migration.md`

## Current Data Flow

```text
Browser dashboard
  -> FastAPI REST endpoints
      -> image/frame upload or JSON request parsing
      -> YOLOv8 detector / mock detections
      -> IoU tracker and line-crossing detection
      -> face detection and SFace embedding extraction
      -> known template cosine matching
      -> unknown identity re-identification
      -> SQLAlchemy persistence
      -> dashboard responses for events, sessions, occupancy, hourly stats
```

The browser E2E smoke test in `surfaces/browser/tests/e2e/` mocks backend API
responses. It proves dashboard rendering, navigation, CSV export, and analytics
display, but it is not a real backend or camera integration test.

## Persistence Model

Primary product tables are represented by SQLAlchemy models in `app/models.py`:

- `users`
- `persons`
- `face_templates`
- `unknown_identities`
- `cameras`
- `camera_configs`
- `events`
- `visit_sessions`

`face_templates.embedding_vector` and `unknown_identities.embedding_vector` use
a custom `VectorType(128)` that maps to pgvector on PostgreSQL and JSON text on
SQLite. The product docs mention older 512-dimensional ArcFace assumptions in
places; current runtime code uses SFace 128-dimensional embeddings.

## Boundary Rules

Unknown input must be parsed at the API boundary before entering tracking,
matching, or persistence code. Current boundary inputs include:

- Uploaded image files in `/api/process-frame` and `/api/persons/register`.
- Form fields such as `session_id`, `line_config`, and `mock_detections`.
- Camera source URLs for webcam, file, and RTSP sources.
- Query parameters such as `/api/sessions?date=YYYY-MM-DD`.
- Environment variables in `app/database.py` and service configuration.
- Database rows converted into API responses.

Current gaps before production use:

- Authentication and authorization are not implemented for API routes.
- CORS is currently permissive and should be narrowed before deployment.
- File upload size, image dimensions, and RTSP connection timeouts need explicit
  limits.
- Health checks report configuration presence rather than actively pinging
  PostgreSQL and Redis.

## Dependency Rule

The implemented code is currently pragmatic and route-centric rather than fully
layered. Preserve these boundaries for future changes:

| Layer | Current files | Rule |
| --- | --- | --- |
| Domain logic | `app/geometry.py`, `app/tracker.py` | Keep pure line-crossing and tracking rules independent from FastAPI, database, and UI code. |
| AI infrastructure | `app/detector.py`, `app/face_pipeline.py` | Own model loading and inference details; callers should pass images and receive structured detections or embeddings. |
| Persistence | `app/database.py`, `app/models.py`, `app/alembic/` | Own connection setup, models, vector compatibility, and migrations. |
| Interface/API | `app/main.py` | Parse requests, call pipeline/persistence code, and format API responses. Avoid growing more domain rules here when adding larger features. |
| Browser surface | `surfaces/browser/src/` | Consume public API contracts only; do not depend on backend internals. |

When a feature grows beyond a narrow route change, prefer extracting application
services from `app/main.py` instead of adding more stateful logic directly to
route handlers.

## Performance Notes

Known hot paths:

- `/api/process-frame` loads all active face templates for every frame and
  computes cosine similarity in Python.
- Unknown re-identification loads all active unknown identities and compares
  vectors in Python.
- Face detection and embedding extraction run synchronously inside the FastAPI
  request path.
- `session_trackers` is an in-memory dictionary keyed by client-provided
  `session_id`, so memory can grow without eviction.
- Event/session/analytics list endpoints currently return all matching rows
  without pagination.

The PostgreSQL target includes pgvector and HNSW indexes. Future performance
work should move vector similarity lookup into PostgreSQL or a bounded cache,
add pagination, and introduce tracker/session eviction.

## Security Notes

The current application is demo-oriented. Before production or shared network
deployment, treat these as required stories:

- Add authentication and role-based authorization for staff/admin workflows.
- Restrict CORS to configured dashboard origins.
- Validate upload content type, file size, image dimensions, and camera source
  URLs.
- Add request timeouts for camera/RTSP probing.
- Define biometric retention for known templates and unknown identities.
- Avoid returning internal exception strings in API responses.
- Replace `print` logging with structured logs that do not expose sensitive
  paths, URLs, or biometric pipeline details.

## Observability Contract

The server should eventually emit one canonical JSON log line per request with:

- timestamp
- level
- request_id
- user_id when known
- action
- duration_ms
- status_code
- message

Audit logs are product records. Application logs are operational records. Do not
use one as a substitute for the other.
