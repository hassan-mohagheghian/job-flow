# Prompt 236 - Fix Job Detail dismiss action and move expired/dismiss actions to the second column

## Objective

Make **Mark as dismissed** actually work in the Job Detail drawer (the button
currently toggles a state flag but renders no dialog, so nothing happens), and
move **Mark expired** / **Mark as dismissed** out of the cramped Tracking
sub-column into a stacked action group in the drawer's second column, right
after **Work Types**.

## Current State

- `apps/frontend/src/features/jobs-v2/components/JobDetailDrawer.tsx`
  - `JobDetailContent` owns `isDismissOpen`, `dismissMutation` and
    `handleDismissToggleChange` (`:553-569`), and renders a **Mark as dismissed**
    button inside the Tracking row (`:665-672`).
  - `DismissDialog` is neither imported nor rendered — clicking the button only
    flips `isDismissOpen`, so the action is silently dead.
  - Tracking row layout (`:646-674`): status select in one sub-column;
    `TrackingActions` (Mark applied + Mark expired) and the dismiss button
    stacked in the other.
  - Second details column (`:679-692`): Employment / Salary / Work Types only.
- `TrackingActions` (`TrackingActions.tsx`) always renders both quick actions;
  it has no way to render a single action in a given location.
- `DismissDialog` (`DismissDialog.tsx`) already implements title, optional note,
  Ctrl+Enter and pending state; it just needs to be wired back in.

## Changes

1. **`TrackingActions.tsx`** — add optional
   `statuses?: ReadonlyArray<ApplicationStatus>`; filter `QUICK_ACTIONS` by it
   (preserving their existing order) and keep the default (both actions).
2. **`JobDetailDrawer.tsx`**
   - Re-introduce a local `DismissAction` component (same behaviour as the old
     `DismissToggle`): renders **Undismiss** directly when `dismissed`, else a
     **Mark as dismissed** button that opens `DismissDialog`; mutation calls
     `jobApi.setDismissed`, invalidates `job-detail` / `jobs-v2-infinite` /
     `jobs`, closes the dialog on success. Delete the dead state/mutation from
     `JobDetailContent`.
   - Tracking row: select + `<TrackingActions statuses={['applied']}>` only.
   - Second column after **Work Types**: an `Actions` row stacking
     `<TrackingActions statuses={['expired']}>` and `<DismissAction>`.
3. **Docs** — update `docs/ux/features/jobs/tracking.md` and
   `docs/ux/DESIGN.md` wireframes/prose, and correct
   `docs/ux/features/jobs/dismissed-jobs.md` (trigger is the Job Detail drawer,
   not a row `×`).

## Testing Requirements

- `TrackingActions.test.tsx`: `statuses={['expired']}` renders only Mark expired;
  default still renders both.
- `JobDetailDrawer.test.tsx`: mock `jobApi.setDismissed`; clicking
  **Mark as dismissed** opens the Dismiss dialog and submitting a note calls
  `setDismissed('job-1', true, note)`; a dismissed job renders **Undismiss** and
  clicking it calls `setDismissed('job-1', false, undefined)`; keep the existing
  quick-action select test green (all three actions still rendered, now in two
  locations).
- Run `./scripts/docker-test.sh frontend` (AGENTS.md rule 18), then
  `npm run lint` and `npm run typecheck`.

## Constraints

- Frontend-only change; no backend route, migration or version bump.
- Respect AGENTS.md 13 (UX wireframes), 17 (no generated files), 18 (Docker
  tests), and keep the two-step create-then-patch behaviour in `TrackingActions`.
