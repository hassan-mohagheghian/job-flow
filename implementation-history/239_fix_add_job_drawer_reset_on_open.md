# Prompt 239 - Reset the Create Entity drawer on every open

## Objective

Make every new Job creation start from an empty form. Today the shared Create
Entity drawer only clears the URL field when it is opened; a successful submit
closes the drawer programmatically, which bypasses the drawer's on-close reset,
so Job Title, Additional Links, Notes and any half-typed Link/Note drafts from
the previous job survive into the next Add Job (and Add Company) drawer.

## Current State

- `apps/frontend/src/shared/components/CreateEntityDrawer.tsx`
  - Form state (URL, title, company name, primary link/title, links, notes and
    their draft inputs) lives in the component, which stays mounted while the
    drawer is closed.
  - `handleOpenChange` (`:...`) resets everything, but it only runs for
    user-initiated closes (Cancel, X, Escape/overlay).
  - On success the parents call `onAddJobDrawerOpenChange(false)` /
    `setDrawerOpen(false)` directly (`JobsPage.tsx`, `GlobalAddJobProvider.tsx`,
    `CompaniesPage.tsx`), so `handleOpenChange` never runs and stale state is
    kept.
  - The open effect only resets `urlInput` / `primaryUrl` before applying the
    gesture-captured clipboard URL.
- Clipboard prefill is a documented feature (`docs/ux/features/jobs/add-job.md`,
  `docs/ux/features/companies/add-company.md`); it must keep working, including
  replacing the URL when a paste/drop happens while the drawer is already open.

## Changes

1. `CreateEntityDrawer.tsx`
   - Extract a `resetForm()` callback that clears every field and draft panel.
   - Track the previous `open` value in a ref. On an `open` transition:
     - `false`: when it was `true`, run `resetForm()` (covers programmatic
       closes after Add).
     - `true` from `false`: run `resetForm()`, then apply the clipboard prefill.
   - Keep the existing reactive URL replacement when `clipboardUrl` changes while
     the drawer is already open, but do not wipe the other fields in that case.
   - Have `handleOpenChange(false)` use `resetForm()`.
2. Docs: `docs/ux/features/jobs/add-job.md` (Default state + Clipboard Prefill),
   `docs/ux/features/companies/add-company.md`, and the Add Job note in
   `docs/ux/DESIGN.md` state that every open starts from an empty form and that
   only the clipboard URL is prefilled.

## Testing Requirements

- `apps/frontend/src/shared/components/CreateEntityDrawer.test.tsx`
  - Job mode: fill title, add a link and a note, close programmatically
    (`open=false` without `onOpenChange`), reopen with an empty clipboard →
    every field is empty and draft panels are closed.
  - Company mode: same for company name, primary title, links and notes.
  - While open, changing `clipboardUrl` replaces only the URL and preserves the
    other entered values.
- Run `./scripts/docker-test.sh frontend`, then `npm run lint` and
  `npm run typecheck` (AGENTS.md rule 18).

## Constraints

- Frontend-only change; no backend, migration or version bump.
- Keep the clipboard-captured-in-gesture behaviour and all existing clipboard
  prefill tests green.
- Respect AGENTS.md rules 13 (UX docs + wireframe), 17 (no generated files) and
  18 (Docker-only tests).
