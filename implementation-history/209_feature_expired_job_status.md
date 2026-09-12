# Prompt 209 - Expired Job Status

## Objective

Let users mark a job as **expired** (posting no longer accepting
applications) via the existing application-funnel status. Word choice:
**expired** — universal job-board term (LinkedIn/Indeed: "this job has
expired"); `closed` is ambiguous (closed by whom? drawer closed?),
`no_longer_accepting` is verbose novel vocabulary. `expired` sits alongside
the posting-side terminals without overloading candidate-side
`rejected`/`withdrawn`.

## Current State

- `ApplicationStatus.ALL` (`apps/backend/applications/domain/entities/application.py:47`)
  = seen, preparing, ready_to_apply, applied, interview, offer, accepted,
  rejected, withdrawn. `SELECTABLE` = all but `seen`.
- Validation (`application_service.py:140`) is against `ALL` — additive change
  flows through service, timeline, generic `ApplicationStatusChanged` event.
- `status` columns are plain `String`, no DB constraint
  (`application_model.py:35,50`) — **no migration needed**.
- `TRACKING_STATUSES` (`apps/backend/jobs/presentation/api/jobs_v2_router.py:62`)
  mirrors the funnel + `not_applied`.
- Frontend: `ApplicationStatus` (`entities/application/types.ts`),
  `TrackingStatus` (`entities/job/types.ts:97`), `TrackingBadge.tsx`,
  `ApplicationStatusBadge.tsx`, `ApplicationTracker.tsx:18` options,
  `JobsToolbar.tsx:48` filter labels.
- No `expired` value exists anywhere; backend tests only assert invalid
  statuses (no exhaustive lists to update).

## Implementation Steps

1. Backend `application.py`: add `EXPIRED = "expired"`; append to `ALL` and
   `SELECTABLE`; update docstring terminals (`rejected / withdrawn` →
   `rejected / withdrawn / expired`, noting expired is posting-side).
2. Backend `jobs_v2_router.py`: add `"expired"` to `TRACKING_STATUSES`.
3. Frontend `entities/application/types.ts`: add `| 'expired'`.
4. Frontend `entities/job/types.ts`: add `| 'expired'` to `TrackingStatus`.
5. `TrackingBadge.tsx`: `expired: orange tint, label 'Expired'`.
6. `ApplicationStatusBadge.tsx`: same entry (typed `Record<ApplicationStatus,…>`
   requires it).
7. `ApplicationTracker.tsx` `STATUS_OPTIONS`: append `'expired'`.
8. `JobsToolbar.tsx` `TRACKING_FILTER_LABELS`: `expired: "Expired"`.
9. Tests (TDD, first): add `{ status: 'expired', label: 'Expired' }` to
   `ApplicationStatusBadge.test.tsx` cases.
10. Docs: `docs/domain/applications/application.md` status table — add
    `expired` row (table is stale: says `recommended`, code is `seen`; fix the
    table to match code while touching it).

## Testing Requirements

- `./scripts/docker-test.sh backend` (applications + jobs suites cover
  validation/filter paths).
- `./scripts/docker-test.sh frontend` (badge test with new case).
- Manual: set a job to Expired via Application Tracker → badge + timeline +
  jobs-list filter show it; `PATCH /api/applications/{id}` with
  `{"status":"expired"}` returns 200.

## Constraints

- No new domain event (generic `ApplicationStatusChanged` carries the status).
- No migration (plain string columns).
- No FK changes (rule 15); funnel semantics unchanged — expired is a terminal
  like rejected/withdrawn, reachable from any state.
