# Prompt 238 - Default pagination page size to 10 with 10-step options

## Objective

Make the Dashboard **Sources** table open at **10 rows per page** and keep the
rows-per-page choices in **steps of 10** (10, 20, 30, …, 100). Apply the same
10-item step to the other paginated/infinite lists (Jobs, Companies, Skills,
Cities) so the app uses one consistent page-size unit.

## Current State

- `features/dashboard/hooks/useSources.ts` starts with `page_size: 25`.
- `features/dashboard/components/SourcesTable.tsx` offers `[10, 25, 50, 100]`.
- `shared/config/constants.ts` uses `PAGE_SIZE = 30` (Jobs infinite) and
  `PAGE_SIZE_SMALL = 25` (Companies / Skills / Cities infinite).
- The sources API defaults to `page_size=25` in the router, repository and API
  documentation.

## Changes

1. `shared/config/constants.ts`
   - `PAGE_SIZE = 10`, `PAGE_SIZE_SMALL = 10`.
   - Export `PAGE_SIZE_OPTIONS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]`.
2. Dashboard Sources
   - `useSources.ts` default query `page_size: 10` (via `PAGE_SIZE_SMALL`).
   - `SourcesTable.tsx` renders `PAGE_SIZE_OPTIONS` (still resets to page 1 on
     change).
   - Backend `GET /api/jobs/sources` default `page_size` becomes `10` (router +
     repository signature) to match the UI default.
3. Other paginated pages
   - Backend defaults for Jobs (`/api/jobs/list`), Companies, Skills and Cities
     become `10` (`Query`, use-case and repository signatures; shared
     `DEFAULT_PAGE_SIZE` fallback too).
   - No cursor/request shape changes — only the default chunk size.
4. Tests / docs
   - Dashboard tests use page size 10 and expect the next option to be 20.
   - Backend sources test asserts the default page returns 10 of 11 rows.
   - Update `docs/ux/features/dashboard/page.md`,
     `docs/api/jobs/job-sources-dashboard.md`, `docs/api/jobs/list-jobs.md`,
     `docs/api/companies/list-companies.md`, `docs/api/skills/list-skills.md`,
     `docs/api/cities/list-cities.md`, and the Jobs / Companies / Skills /
     Cities UX pages and flows from 25/50 to 10.
   - Note the page-size selector remains server-side and capped at 100.

## Testing Requirements

- `./scripts/docker-test.sh frontend` — SourcesTable selector now starts at 10
  and advances to 20; dashboard renders with `pageSize=10`.
- `./scripts/docker-test.sh backend` — sources list default page size is 10;
  explicit `page_size` still works.
- Typecheck the frontend.

## Constraints

- No API shape change, no migration, no version bump.
- Keep `HISTORY_PAGE_SIZE` (generation-history drawer) unchanged — it is a
  background history fetch, not a user-facing page step.
- Follow AGENTS.md 13 (docs), 17 (no generated files) and 18 (Docker tests).
