# Overview

## Current Behavior

- `unknown_identities.expire_at` is set at creation (1-7 days) but no background process enforces it — expired rows remain active and participate in re-identification queries.
- Events, visit sessions, and face_templates accumulate indefinitely with no retention window.
- No audit trail exists for staff actions (enrollment, deletion) or system data lifecycle events.
- No configuration mechanism for retention periods — all values are hardcoded or missing.
- Biometric templates (`face_templates.embedding_vector`) persist until manually deleted; no policy for automatic anonymization or purging after person deactivation.

## Target Behavior

- A background retention job (or API-triggered command) expires unknown identities past their `expire_at`, purges events/sessions older than a configurable window, and purges face_templates for deactivated persons after a grace period.
- An `audit_log` table records staff actions and system retention/expiry actions with actor, action, target, detail, and timestamp.
- Retention periods are configurable via environment variables with sensible defaults.
- A read-only retention status endpoint exposes current row counts and pending expirations.
- The retention job logs its actions to `audit_log` and can be run on demand or on a schedule.

## Affected Users

- Staff (librarians/admins): benefit from automatic data lifecycle management, audit visibility.
- Known persons (library members): biometric data is retained only while active; deactivated persons' templates are purged after a configurable grace period.
- Unknown visitors: re-identification vectors expire per the existing `expire_at` policy — now enforced.
- System operators: audit trail for compliance and incident investigation.

## Affected Product Docs

- `docs/product/data-model.md`
- `docs/product/overview.md`
- `docs/ARCHITECTURE.md` (security notes section)

## Non-Goals

- No GDPR/CCPA-specific compliance workflow (right to erasure request portal, data export UI) — this is operational retention, not a compliance portal.
- No UI for configuring retention periods (env-var driven only for now).
- No PII/anonymization of events or visit_sessions beyond what retention purging provides.
- No integration with external audit/SIEM systems.
- No real-time retention enforcement at write time — only batch cleanup.
- No automatic backup before purge — operator is responsible for data backup.
