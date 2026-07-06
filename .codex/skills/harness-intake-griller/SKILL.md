# Harness Intake Griller

Use this project-scoped skill when a request needs discussion, feature intake,
docs, story shaping, or recommendation before Symphony execution.

## Required Reads

Before shaping work, read:

- `AGENTS.md`
- `README.md`
- `docs/HARNESS.md`
- `docs/FEATURE_INTAKE.md`
- `docs/ARCHITECTURE.md` for structural or implementation work
- `docs/CONTEXT_RULES.md`
- `docs/TOOL_REGISTRY.md`
- `scripts/bin/harness-cli.exe query matrix` on Windows

If the request touches an existing product behavior, also read the relevant
files under:

- `docs/product/`
- `docs/stories/`
- `docs/decisions/`

## Intake Output

Classify the request before implementation:

- Input type: new spec, spec slice, change request, new initiative,
  maintenance request, or harness improvement.
- Lane: tiny, normal, or high-risk.
- Affected product docs and stories.
- Expected validation proof.
- Whether the request should become direct work, a story packet, or a
  high-risk story folder.

Record the classification with:

```powershell
.\scripts\bin\harness-cli.exe intake --type "<type>" --summary "<summary>" --lane <lane>
```

## Grilling Checklist

Ask or resolve these before execution:

- What concrete product behavior changes?
- Which existing contract or story owns it?
- What should not change?
- What proof will be enough?
- Does the request touch auth, authorization, data model, audit/security,
  external systems, public contracts, existing behavior, or multiple domains?
- Is a durable decision required?

Prefer a small vertical story over a broad implementation plan. If the user
only asks for advice, stay read-only except for Harness intake/trace records.

## Before Finishing

- Keep affected docs, story packets, and durable proof records current.
- Run available verification commands for the selected lane.
- Record a trace with `.\scripts\bin\harness-cli.exe trace`.
- If missing context or repeated friction appears, add or update Harness
  backlog with `.\scripts\bin\harness-cli.exe backlog add`.
