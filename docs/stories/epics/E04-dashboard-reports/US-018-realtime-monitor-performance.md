# US-018 Realtime Monitor Performance and Counting Responsiveness

## Status

implemented

## Lane

normal

## Product Contract

The monitor screen must keep the person box and in/out counter responsive during webcam/video analysis. Counting must continue to be based on virtual-line crossing, while the browser live monitor can use a faster processing mode that avoids expensive face matching on every frame.

## Relevant Product Docs

- `docs/product/overview.md`
- `docs/product/ai-pipeline.md`
- `docs/product/dashboard-and-reports.md`

## Acceptance Criteria

- [x] Browser live monitor sends frames without a fixed 100 ms idle delay after every backend response.
- [x] Browser live monitor requests backend `fast_mode=true` so person tracking/counting is prioritized over per-frame face identification.
- [x] `/api/process-frame` preserves the old default behavior when `fast_mode` is omitted or false.
- [x] `/api/process-frame` returns `processing_ms` so UI and audits can see backend latency.
- [x] Line crossing has a debounce window to avoid duplicate counts when a track oscillates near the line.
- [x] Stale responses from a stopped/restarted analysis session do not redraw old boxes over the current video.

## Design Notes

- API:
  - Added optional form field `fast_mode`.
  - Added optional form fields `identity_probe`, `detect_frame`, and `identity_ttl_seconds`.
  - `fast_mode=false` keeps existing matching behavior for validation scripts and full identity workflows.
  - `fast_mode=true` skips routine face work, except for explicit identity probes and crossing events.
  - `detect_frame=false` lets the backend skip YOLO and advance active tracks with tracker prediction.
- Backend:
  - Detector session now enables ONNX graph optimization and prefers CUDA or DirectML providers when available, with CPU fallback.
  - Tracker defaults now use shorter lost-track retention and a crossing debounce.
  - Tracker predicts BBox position from per-track velocity during skipped/missed detector frames.
  - Face templates are cached briefly and invalidated when people are registered or deleted.
- UI:
  - Webcam asks for 30 FPS.
  - JPEG capture quality is reduced to lower upload/decode cost.
  - The loop schedules the next frame from the actual elapsed processing time instead of sleeping for a fixed 100 ms after every response.
  - Browser sends detector frames on a cadence and keeps identity probes periodic so known-person labels refresh without matching every frame.
  - Monitor metadata shows backend latency.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | Tracker crossing debounce remains covered by crossing validation |
| Integration | `python scripts/validate_realtime_fast_mode.py` |
| E2E | Existing browser dashboard smoke remains optional because it mocks backend |
| Platform | `npm --prefix surfaces/browser run build` on Windows |
| Release | Real camera FPS benchmark not automated yet |

## Harness Delta

- No harness policy change.
- Performance benchmark capability is not registered in the tool registry, so real camera FPS remains manual evidence for now.

## Evidence

- 2026-07-09 realtime performance pass:
  - `python scripts/validate_realtime_fast_mode.py` passed; proof response included `fast_mode=true`, `processing_ms`, and one ENTRY crossing event.
  - `python scripts/validate_crossing.py` passed; default `/api/process-frame` still emits ENTRY crossing events.
  - `python scripts/validate_matching.py` passed; default `fast_mode=false` still recognizes KNOWN identity and logs ENTRY then EXIT.
  - `npm --prefix surfaces/browser run build` passed.
  - `npm --prefix surfaces/browser run lint` passed with existing React hook dependency warnings in `App.tsx`.
  - `.\scripts\bin\harness-cli.exe story verify US-018` passed.

- 2026-07-09 follow-up after live camera review:
  - Restored live identity recognition in browser fast mode with periodic `identity_probe` requests.
  - Enriched `crossing_events` with `identity_type`, `person_name`, and `similarity_score` so the activity log records the same identity the backend used for event persistence.
  - Moved ENTRY/EXIT counters below the video frame so they no longer cover the person box.
  - Set the default line to a vertical center line and added Vao/Ra direction arrows to the canvas overlay.
  - `python scripts/validate_realtime_fast_mode.py` passed and now proves `fast_mode=true` plus `identity_probe=true` can return a KNOWN person name.
  - `python scripts/validate_matching.py`, `python scripts/validate_crossing.py`, `npm --prefix surfaces/browser run build`, `npm --prefix surfaces/browser run lint`, and `.\scripts\bin\harness-cli.exe story verify US-018` passed.

- 2026-07-09 vertical-line counting fix:
  - Root cause: tracker always used the bbox bottom-center point. That worked for horizontal lines but missed side-to-side movement across the new vertical default line when the person's feet were below the finite line segment.
  - Tracker now uses bbox center for vertical lines and bottom-center for horizontal lines.
  - Default browser line now spans the full video height: `[[320, 0], [320, 480]]`.
  - `scripts/validate_crossing.py` now includes a vertical crossing API scenario.
  - `python scripts/validate_crossing.py`, `python scripts/validate_matching.py`, `python scripts/validate_realtime_fast_mode.py`, `npm --prefix surfaces/browser run build`, `npm --prefix surfaces/browser run lint`, and `.\scripts\bin\harness-cli.exe story verify US-018` passed. Lint still reports the pre-existing React hook dependency warnings.

- 2026-07-09 detector cadence and BBox prediction optimization:
  - Root cause: live BBox lagged because each browser frame waited for full detector work; when detections arrived late, the tracker only returned boxes with `lost == 0`, so the overlay could not move until the next detector result.
  - Backend now supports `detect_frame=false`; skipped frames avoid YOLO and the tracker predicts active BBox positions from smoothed per-track velocity.
  - Browser now runs detector on initial frames, identity probe frames, and then every third processed frame; intermediate frames use prediction to keep the overlay responsive.
  - Identity results are cached per track with a configurable TTL, and face templates use a short in-memory cache invalidated by registration/deletion.
  - `scripts/validate_realtime_fast_mode.py` now proves a skipped detector frame returns `detector_ran=false`, `detect_frame=false`, and a predicted track.
  - `python scripts/validate_crossing.py`, `python scripts/validate_matching.py`, `python scripts/validate_realtime_fast_mode.py`, `npm --prefix surfaces/browser run build`, `npm --prefix surfaces/browser run lint`, and `.\scripts\bin\harness-cli.exe story verify US-018` passed. Lint still reports the pre-existing React hook dependency warnings in `App.tsx`.
