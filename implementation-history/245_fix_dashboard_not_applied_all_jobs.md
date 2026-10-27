# Prompt 245 - Count every pre-application job in the Dashboard Not applied slice

## Objective

Make the Dashboard "Applications by status" doughnut's **Not applied** slice count
every job that has not reached `applied` yet — jobs with no application record plus
jobs whose application is still `seen` / `preparing` / `ready_to_apply` — instead of
counting only tracked pre-application application records.

## Current State

- `apps/frontend/src/features/dashboard/components/ApplicationStatusChart.tsx:47-97`
  builds slices from `GET /api/applications/status-distribution`; `Not applied`
  only aggregates `seen` + `preparing` + `ready_to_apply` from application rows.
- `apps/backend/applications/infrastructure/repositories/sa_application_repository.py:72-93`
  counts application rows only, so a job without an application is absent.
- Jobs are already counted per user in the Jobs context
  (`apps/backend/jobs/infrastructure/repositories/sa_job_repository.py:234-249`),
  and `count_created_by_day` (`:196-232`) already joins `ApplicationModel` for the
  timeline. Tracking statuses (`not_applied` + the application funnel) are defined
  in `apps/backend/jobs/presentation/api/jobs_v2_router.py:65-79` and
  `docs/ux/features/jobs/tracking.md:14-33`.
- Dashboard spec: `docs/ux/features/dashboard/page.md:115-131`;
  `docs/ux/DESIGN.md:912-929`.

## Changes

1. **Backend Jobs context (owns the all-jobs denominator)**
   - Add `SQLAlchemyJobRepository.application_status_distribution()`: one
     `LEFT JOIN` from non-deleted, user-scoped `JobModel` to `ApplicationModel`
     on `(job_id, user_id)`, grouped by application status. `NULL` joins count as
     `not_applied`; items are ordered `not_applied` first, then
     `ApplicationStatus.ALL`; `total` is every non-deleted job.
   - Add `GET /api/jobs/tracking-status/distribution` to the jobs-v2 router +
     response schemas in `jobs_v2.py` (`{items:[{status,count}], total}`).
   - Keep `GET /api/applications/status-distribution` unchanged as the
     application-record aggregate; the Dashboard stops using it.
2. **Frontend**
   - Add `JobApplicationStatusDistribution` types + `sourceApi.applicationStatusDistribution()`
     in `apps/frontend/src/entities/job/sources.ts`.
   - `useApplicationStatusDistribution` (`features/dashboard/hooks/useSources.ts:34`)
     fetches the jobs endpoint.
   - `buildApplicationStatusSlices` adds the `not_applied` bucket to the
     `seen` / `preparing` / `ready_to_apply` counts, uses `total` jobs as the
     percentage denominator, and the legend reads "`N` total jobs". Empty state
     becomes "No jobs yet — import jobs to populate this chart."
   - Keep the cache key invalidated on application create/update; also invalidate
     it when a job is created or deleted.
3. **Docs**
   - `docs/api/jobs/job-sources-dashboard.md`: document the new jobs aggregate.
   - `docs/api/API.md`: list the new endpoint.
   - `docs/api/applications/README.md`: note the chart now reads the jobs aggregate.
   - `docs/ux/features/dashboard/page.md` + `docs/ux/DESIGN.md`: new slice
     semantics, jobs denominator, empty state, data-flow endpoint.

## Testing Requirements

- Backend: repository/API tests for (a) jobs without applications in `not_applied`,
  (b) pre-application statuses stay their own buckets, (c) applied+ statuses count,
  (d) deleted/other-user jobs and applications excluded, (e) empty payload.
- Frontend: update `Dashboard.test.tsx` fixtures and assertions (Not applied =
  no-application + pre-application jobs, percentage against all jobs, total label,
  empty state) and add an API URL test in `entities/job/api.test.ts`.
- Run `./scripts/docker-test.sh backend` and `./scripts/docker-test.sh frontend`
  (AGENTS.md rule 18), then `cd apps/frontend && npm run lint && npm run typecheck`.

## Constraints

- No migration, no schema change, no new domain event (read-only aggregate).
- Jobs context owns the jobs-based aggregate; do not query `job.jobs` from the
  Applications context. Respect AGENTS.md rules 1, 2, 10, 13, 15, 17, 18.
- Keep the applications `status-distribution` endpoint and its tests intact.
