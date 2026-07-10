# Story Backlog

The initial LibCounterAI demo buildout has been sliced into implemented story
packets under `docs/stories/epics/`.

Do not create every possible story packet up front. Create story packets when
the work is selected or when a product decision needs a durable place to land.

## Current Epics

| Epic | Description | Status |
| --- | --- | --- |
| E01 Web Demo | Setup, person detection/tracking, database setup, line crossing, browser dashboard, camera API | implemented |
| E02 Known Person | Face pipeline, enrollment API, real-time face matching and event logging | implemented |
| E03 Unknown Visitor | Unknown re-identification, visit sessions, session API/UI sync | implemented |
| E04 Dashboard Reports | CSV export, date filtering, known/unknown analytics breakdown, browser smoke proof, demo seed data; one-command local dev stack in progress | implemented |

## Recommended Next Stories

| Candidate | Why it matters | Suggested lane |
| --- | --- | --- |
| Unit proof sweep | Adds focused unit tests around line crossing, session state, analytics aggregation, and identity matching thresholds. | normal |
| Privacy and retention hardening | Clarifies biometric retention, unknown identity expiry, audit logging, and operational safeguards before production use. | high-risk |
| Auth and staff roles | Adds real librarian/admin access control if this moves beyond a controlled demo. | high-risk |
