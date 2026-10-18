# Prompt 230 - UX: Mark applied action + stacked tracking actions in the Job Detail drawer

## Objective

The Job Detail drawer's **Tracking** row must let the user (a) set the job to
**applied** with one click, and (b) see the three quick actions —
**Mark applied**, **Mark expired**, **Mark as dismissed** — laid out so they fit
the drawer's narrow two-column header grid: **the status select alone in one
sub-column, the three buttons stacked vertically in the other**.

## Current State (after Prompt 229)

- `JobDetailDrawer.tsx:650-672`: the "Tracking" `DetailRow` value is a single
  horizontal `flex gap-3` with `<TrackingStatusSelect>` (150px) next to the
  **Mark as dismissed** button (120px). Inside the parent
  `grid grid-cols-2 gap-12` (`:616`) this row is cramped: two wide controls side
  by side overflow the left column.
- No **Mark applied** action exists anywhere — reaching `applied` requires
  opening the select and picking it.
- `TrackingStatusSelect.tsx:55-66`: when a job has **no application**, the
  component itself renders an inline **Mark expired** button. That is correct
  for the other two callers (`JobEditDrawer.tsx:207`,
  `CreateEntityDrawer.tsx:151`) but conflicts with the drawer redesign, where
  *the drawer* owns the action-button column (it would duplicate Mark expired).

## Implementation Steps

1. **New** `apps/frontend/src/features/jobs-v2/components/TrackingActions.tsx`
   — stacked quick actions that set the application status, working **with or
   without** an existing application (create → then patch, same two-step the
   legacy Mark expired used):
   - Renders `Mark applied` (→ `applied`) and `Mark expired` (→ `expired`) as
     full-width `Button`s in a fragment (callers decide the column layout).
   - `useApplicationByJobQuery` decides patch-vs-create; on success invalidate
     `['jobs-v2-infinite']`, `['job-detail', jobId]`, `['jobs']`.
   - Props: `{ jobId: string; className?: string }`; disable both while a
     mutation is pending ("Saving…").
2. **`TrackingStatusSelect.tsx`**: add `emptyMode?: 'button' | 'placeholder'`
   (default `'button'` → unchanged legacy behaviour for JobEditDrawer /
   CreateEntityDrawer). `'placeholder'` renders a **disabled** select whose
   `SelectValue` placeholder reads **"Not applied"** (keeps
   `aria-label="Tracking status"`), so callers can render their own buttons.
3. **`JobDetailDrawer.tsx`** Tracking row → two sub-columns:
   - left (`flex-1 min-w-0`): `<TrackingStatusSelect jobId emptyMode="placeholder" />`
   - right (`w-[120px] shrink-0 flex flex-col gap-1`):
     `<TrackingActions jobId={detail.id} />` then the existing
     **Mark as dismissed / Undismiss** button (drawer-level dismiss mutation and
     dialog stay in the drawer, untouched).

## Testing Requirements

- `TrackingStatusSelect.test.tsx`: new case — `emptyMode="placeholder"` with no
  application renders **no** Mark expired button and shows the disabled
  "Not applied" select. Existing 3 tests unchanged.
- **New** `TrackingActions.test.tsx` (mock `applicationApi` like the sibling
  tests): renders both buttons; Mark applied with no application →
  `create('job-1', undefined)` then `update(id, { status: 'applied' })`; Mark
  applied with an existing application → `update(..., { status: 'applied' })`
  and **no** create; Mark expired → `update(..., { status: 'expired' })`.
- `JobDetailDrawer.test.tsx`: existing combobox test must stay green; add — the
  stacked column renders all three actions, and clicking **Mark applied**
  (application already mocked as existing) calls
  `applicationApi.update('app-1', { status: 'applied' })`.
- Verify: `./scripts/docker-test.sh frontend` (rule 18) + `npm run typecheck`
  (baseline: 40 pre-existing errors, none in touched files).

## Docs

- `docs/ux/features/jobs/tracking.md` §Job Detail / Job Edit Drawers: replace
  the drawer wireframe with the new sub-column layout (select alone / buttons
  stacked), document **Mark applied** and the `emptyMode="placeholder"`
  "Not applied" state, and add a small mermaid flowchart of the
  create-then-patch action path. Keep the existing funnel mermaid.

## Constraints

- AGENTS.md 13 (wireframe docs), 18 (Docker tests), 17 (no generated files),
  11 (no `print`).
- No backend change, no version bump, no migration.
- Do not touch `JobEditDrawer` / `CreateEntityDrawer` behaviour (default
  `emptyMode` preserves it) or the drawer's dismissal flow.
