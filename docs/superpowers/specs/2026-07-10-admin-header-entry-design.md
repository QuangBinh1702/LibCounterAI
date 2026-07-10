# Admin header entry and UI polish

**Date:** 2026-07-10  
**Status:** approved for implementation  
**Lane:** normal change request

## Problem

Admin is used occasionally (a few times per week). Putting it in the primary nav competes with daily ops tabs (Monitor, Registry, History, Analytics).

## Decision

Move Admin entry out of primary `NavTabs` into a header Shield button (ADMIN-only), next to ThemeToggle. Keep the same in-app view switch (no new router). Polish Admin page UX within existing design tokens.

## Scope

### In

- Remove Admin from primary nav
- Add header Shield control (`data-testid="admin-entry"`), visible only when `isAdmin`
- Toggle: open Admin from current tab; click again or "Quay lại" returns to previous ops tab
- Admin UI polish: segmented sub-nav, labeled create-user form, skeleton loading, empty states, cleanup confirm
- Preserve APIs, role gate, and three panels (users / audit / retention)

### Out

- Separate `/admin` shell or React Router
- New admin features (edit/delete user, retention config editing)
- Design-system migration (Fluent/Carbon)

## Proof

- Component/unit coverage for header entry visibility and navigation behavior
- `npm` lint + build for `surfaces/browser`
