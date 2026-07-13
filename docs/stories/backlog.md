# Story Backlog

The initial LibCounterAI demo buildout has been sliced into implemented story
packets under `docs/stories/epics/`.

Do not create every possible story packet up front. Create story packets when
the work is selected or when a product decision needs a durable place to land.

## Current Epics

| Epic | Description | Status |
| --- | --- | --- |
| E01 Web Demo | Setup, person detection/tracking, database setup, line crossing, browser dashboard, camera API | implemented |
| E02 Known Person | Face pipeline, enrollment API, real-time face matching and event logging, member update CRUD | implemented |
| E03 Unknown Visitor | Unknown re-identification, visit sessions, session API/UI sync | implemented |
| E04 Dashboard Reports | CSV export, date filtering, known/unknown analytics breakdown, browser smoke proof, demo seed data, one-command dev stack, realtime performance, identity continuity | implemented |
| E05 Privacy & Retention | Biometric retention, unknown identity expiry, audit logging, 7-phase cleanup engine | implemented |
| E06 Auth & Roles | Role-based access control, password change, user management, person write guards, RegistryPage role hiding, AdminPage tab filtering, 403 toast | implemented |

## Recommended Next Stories

| Candidate | Why it matters | Suggested lane |
| --- | --- | --- |
| Unit proof sweep | Adds focused unit tests around line crossing, session state, analytics aggregation, and identity matching thresholds. | normal |
