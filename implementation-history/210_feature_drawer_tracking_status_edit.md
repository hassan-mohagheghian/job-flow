# Prompt 210 - Editable Tracking Status in Job Drawers

## Objective

Let users change a job's tracking/application status (incl. `expired` from
prompt 209) directly in the Job Detail drawer, Job Edit drawer, and the
create-drawer duplicate `JobSummaryCard` — without detouring to the
application workspace.

## Current State

- Detail (`JobDetailDrawer.tsx:628`), Edit (`JobEditDrawer.tsx:205`), and
  `JobSummaryCard` (`CreateEntityDrawer.tsx:144`) show a read-only
  `TrackingBadge`; Edit says "Edit in the application workspace".
- Job payloads carry only derived `tracking_status`, never the application id.
- Reusable: `useApplicationByJobQuery(jobId)` (`entities/application/hooks.ts:27`)
  resolves the application; `useUpdateApplicationMutation` (L47) PATCHes status;
  `useCreateApplicationMutation` (L35) creates it. Both invalidate only
  `['application', ...]` — job list/detail caches stay stale.
- Canonical options: `STATUS_OPTIONS` (`ApplicationTracker.tsx:18`, 9 values
  incl. `expired`, excl. `seen`); Select UI pattern at `ApplicationTracker.tsx:73`.
- Job caches: list `['jobs-v2-infinite']`, detail `['job-detail', jobId]`.
- `GET /api/applications/by-job/{job_id}` 404s when no application exists.

## Implementation Steps

1. Export `STATUS_OPTIONS` from `ApplicationTracker.tsx` (avoid option drift).
2. New `features/jobs-v2/components/TrackingStatusSelect.tsx` (`{ jobId }`):
   - `useApplicationByJobQuery(jobId)`; loading → muted placeholder; error/no
     data → "Mark expired" button (create application, then PATCH `expired`,
     chained); application → `Select` with `STATUS_OPTIONS` → update mutation.
   - On every success also invalidate `['jobs-v2-infinite']` and
     `['job-detail', jobId]` (via mutate `onSuccess`); disable while pending.
3. `JobDetailDrawer`: Tracking row uses `<TrackingStatusSelect jobId>`.
4. `JobEditDrawer`: Tracking field uses it (immediate mutation, independent of
   Save); drop the "Edit in the application workspace" hint.
5. `CreateEntityDrawer` `JobSummaryCard`: Application row uses it.
6. Tests (TDD, first): `TrackingStatusSelect.test.tsx` mocking
   `@/entities/application/api` (pattern: `ApplicationTracker.test.tsx:9`) with
   `retry: false` QueryClient — cases: select calls update with chosen status;
   no-application button creates then sets expired; loading state.
7. Docs: `docs/ux/features/jobs/tracking.md` drawers section (now editable) +
   `docs/ux/features/jobs/page.md` if the detail ASCII mentions read-only.

## Testing Requirements

- `./scripts/docker-test.sh frontend` (new test + drawer suites).
- Backend untouched (reuse existing PATCH) — no backend run required.
- Manual: Detail/Edit/duplicate-card → change status → badge, list, and
  timeline update; expired from a job with no application works.

## Constraints

- No backend changes; no new endpoints.
- Immediate mutations (no deferred Save semantics).
- `DuplicateJobDialog.tsx` legacy dialog left alone.
