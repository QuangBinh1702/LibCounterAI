# US-019 Identity Continuity for Unresolved Exit Events

## Status

implemented

## Lane

normal

## Product Contract

When a person exits too quickly for face recognition, the system must not
blindly label the exit as `Khách`. If there is enough session context, the exit
can be resolved from the active visit session. If there is not enough context,
the event must remain `UNRESOLVED` for review instead of being mixed with real
unknown visitors.

## Acceptance Criteria

- [x] EXIT events without a track identity try active-session continuity before falling back.
- [x] If exactly one active visit session exists, the EXIT event inherits that session identity and closes it.
- [x] If zero or multiple active visit sessions exist, the EXIT event is recorded as `UNRESOLVED`.
- [x] Event responses include `identity_resolution` so the UI/log can explain how identity was decided.
- [x] Browser logs display `UNRESOLVED` as `chưa xác định`, not `khách`.
- [x] Known/unknown face-match flows still work as before.

## Design Notes

- `UNKNOWN` means a real anonymous identity record exists or the product has
  decided the person is a visitor with no known profile.
- `UNRESOLVED` means the system could not safely decide at crossing time.
- Session continuity is intentionally conservative: it only auto-resolves when
  there is exactly one active session candidate.
- Event `metadata_json.resolution` records `face_or_track_identity`,
  `session_continuity`, or `unresolved_exit`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Integration | `python scripts/validate_identity_continuity.py` |
| Regression | `python scripts/validate_matching.py` |
| Regression | `python scripts/validate_realtime_fast_mode.py` |
| Platform | `npm --prefix surfaces/browser run build` |

## Evidence

- 2026-07-09 identity continuity implementation:
  - Added session-continuity resolution for unidentified EXIT crossings.
  - Added `UNRESOLVED` fallback for ambiguous unidentified EXIT crossings.
  - Added `identity_resolution` in crossing event responses and event metadata.
  - Added browser log handling for `UNRESOLVED`.
  - `python scripts/validate_identity_continuity.py` passed.
  - `python scripts/validate_matching.py` passed.
  - `python scripts/validate_realtime_fast_mode.py` passed after rerunning sequentially to avoid shared Lena test identity collisions.
  - `python scripts/validate_crossing.py` passed; vertical unidentified EXIT now returns `UNRESOLVED`.
  - `npm --prefix surfaces/browser run build` passed.
  - `npm --prefix surfaces/browser run lint` passed with existing React hook dependency warnings.
