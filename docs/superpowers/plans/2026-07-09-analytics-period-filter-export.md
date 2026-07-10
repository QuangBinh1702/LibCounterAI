# Analytics Period Filter + Export Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox syntax.

**Goal:** Shared day/week/month filters for History + Analytics + Export, premium traffic chart, and Export dropdown (CSV / Excel / PDF).

**Architecture:** Backend accepts `from_date`/`to_date` on sessions and stats endpoints. Frontend owns period presets, shared filter state, vertical traffic chart, and client-side export menu.

**Tech Stack:** FastAPI, React, CSS variables (existing), `xlsx`, `jspdf`, `jspdf-autotable`

---

## Tasks

- [x] Extend API date-range filters
- [x] Add PeriodFilter + date range helpers
- [x] Redesign traffic chart
- [x] Add Export menu (CSV/Excel/PDF) bound to filtered sessions
- [x] Wire History + Analytics to shared filter
- [x] Verify build/lint
