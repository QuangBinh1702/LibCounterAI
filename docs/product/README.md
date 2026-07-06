# Product Docs

This directory contains the living LibCounterAI product contract derived from
`SPEC.md` and the implemented story packets.

Use these files for current behavior. Treat `SPEC.md` as historical input
material unless a new intake explicitly asks to revisit it.

## Current Product Contracts

- `overview.md` - LibCounterAI goals, known/unknown visitor model, visit
  sessions, and counting rules.
- `data-model.md` - PostgreSQL/pgvector/Redis storage model.
- `ai-pipeline.md` - Server-side video, detection, tracking, line crossing,
  face embedding, matching, and unknown re-identification flow.

## Update Rule

When behavior changes:

1. Update the affected product doc.
2. Update or create the story packet.
3. Update durable proof status with `scripts/bin/harness-cli story add` or
   `scripts/bin/harness-cli story update`.
4. Record a decision if the change affects architecture, scope, risk, or a
   previously settled product rule.
