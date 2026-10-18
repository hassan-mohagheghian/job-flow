# Prompt 229 - Fix: Job Detail drawer never renders the Tracking status select

## Problem

`apps/frontend/src/features/jobs-v2/components/JobDetailDrawer.test.tsx:191-196`
("renders an editable tracking status select with the current status") fails
deterministically in every Docker frontend run:

```
TestingLibraryElementError: Unable to find role="combobox" and name "Tracking status"
```

Root cause (not a flaky test — a code/doc drift):

- `JobDetailDrawer.tsx:40` imports `TrackingStatusSelect` but **never renders**
  it (dead import).
- The drawer's "Tracking" `DetailRow` (`JobDetailDrawer.tsx:679-707`) instead
  hand-rolls two buttons: a bespoke **Mark expired** and **Mark as dismissed**.
  There is no way to set `applied / interview / offer / ...` from the detail
  drawer at all.
- The bespoke logic **duplicates** `TrackingStatusSelect` internals:
  `JobDetailContent` holds its own `useApplicationByJobQuery` +
  `useCreateApplicationMutation` + `useUpdateApplicationMutation`
  (`JobDetailDrawer.tsx:557-560`) and its own `handleMarkExpired`
  (`:575-592`) — and it is *worse*: it invalidates `["jobs-v2-infinite"]` and
  `["jobs"]` but forgets `["job-detail", detail.id]` refresh parity is fine,
  yet the `application / isAppLoading / isAppError` destructured values
  (`:558`) are never used anywhere.
- The docs already specify the intended behavior — `docs/ux/features/jobs/tracking.md:62-73`:
  "Both drawers show an editable **Tracking** status (`TrackingStatusSelect`) …
  **Job Detail drawer**: a 'Tracking' row with a status select."
- `TrackingStatusSelect.tsx:51-66` already handles the no-application case
  itself (renders the **Mark expired** button that creates the application and
  sets it to `expired`), so the drawer's duplicate button is redundant.

## Fix (frontend-only)

`apps/frontend/src/features/jobs-v2/components/JobDetailDrawer.tsx`:

1. In the "Tracking" `DetailRow` value, replace the bespoke Mark-expired
   `Button` with `<TrackingStatusSelect jobId={detail.id} />`, keeping the
   **Mark as dismissed** button beside it (flex row preserved).
2. Delete the now-dead duplicate code: `handleMarkExpired`, the
   `application / isAppLoading / isAppError` destructuring, the three
   application mutations/query, and the `@/entities/application/hooks` import
   (`JobDetailDrawer.tsx:6-10`).
3. Result: the row reads `[status select | Mark as dismissed]` when the job has
   an application, and `[Mark expired | Mark as dismissed]` when it does not —
   exactly what `tracking.md` documents.

## Testing

- Existing red test `JobDetailDrawer.test.tsx:191-196` becomes green (the file
  already mocks `applicationApi.getByJob` → `{ status: 'applied' }`, and
  `TrackingStatusSelect` reads through the same hook).
- `TrackingStatusSelect.test.tsx` keeps covering the no-application → Mark
  expired branch.
- Verify with `./scripts/docker-test.sh frontend` (rule 18) plus
  `npm run typecheck` — assert no new errors (repo baseline: 40 pre-existing).

## Docs

- `docs/ux/features/jobs/tracking.md` §Job Detail / Job Edit Drawers: add an
  ASCII wireframe of the drawer's Tracking row (both branches) and clarify that
  **Mark expired** is rendered *by* the select when the job has no application
  (not a separate drawer button), and that **Mark as dismissed** stays next to
  it. Keep the existing mermaid funnel diagram.

## Constraints

- AGENTS.md 13 (UI change → wireframe docs), 18 (Docker tests), 17 (no
  generated files), 11 (structlog, no `print` — N/A here, no Python).
- No backend change, no version bump, no migration.
- Preserve the drawer's existing dismissal flow (`isDismissOpen`,
  `dismissMutation`, `DismissJobDialog`) untouched.
