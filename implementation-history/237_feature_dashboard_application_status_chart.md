# Prompt 237 - Add application status doughnut chart to the Dashboard

## Objective

Add a third Dashboard doughnut chart showing the current user's job application
statuses, focused on the most important funnel outcomes (Applied, Interview,
Offer, Accepted, Rejected). Remaining statuses are folded into an **Other
statuses** slice so every tracked application is counted and percentages always
use the full application total.

## Current State

- Dashboard (`apps/frontend/src/features/dashboard/components/DashboardPage.tsx`)
  renders two doughnuts: listings by source and jobs by recommendation, then
  the sources table.
- Job/source aggregates live in the Jobs context
  (`GET /api/jobs/recommendations/distribution`).
- Applications already expose a per-user `ApplicationModel.status` and
  `SQLAlchemyApplicationRepository` is user-scoped, but there is no aggregate
  endpoint and no Dashboard chart for application status.
- Application statuses are the closed set in
  `applications/domain/entities/application.py`:
  `seen | preparing | ready_to_apply | applied | interview | offer | accepted |
  rejected | withdrawn | expired`.

## Changes

1. **Backend Applications context**
   - `IApplicationRepository.status_distribution()` — count applications by
     status for the repository's user, ordered by the canonical status order,
     omitting zero-count statuses; include `total`.
   - Implement with a single SQLAlchemy `GROUP BY` query (no N+1).
   - `GET /api/applications/status-distribution` returning
     `{ "items": [{ "status": "...", "count": N }], "total": N }` via a Pydantic
     response schema on the Applications router (rule 10 — no route in
     `entrypoints/api.py`).
2. **Frontend**
   - Add `ApplicationStatusDistribution` types and
     `applicationApi.statusDistribution()`.
   - Add `useApplicationStatusDistribution` to the Dashboard hooks, and
     invalidate `application-status-distribution` when an application is
     created or its status is updated.
   - Add `ApplicationStatusChart.tsx` (recharts doughnut, matching the existing
     chart style): fixed order/colors for Applied, Interview, Offer, Accepted,
     Rejected; remaining statuses (seen/preparing/ready_to_apply/withdrawn/
     expired) fold into Other statuses; zero-count slices hidden; legend shows
     count + percentage and the total application count.
   - Render the new panel after "Jobs by recommendation" with the same
     loading/error/retry/empty behavior as the other panels.
3. **Docs**
   - Update `docs/ux/features/dashboard/page.md` (purpose, tree, wireframe,
     chart rules, states, data flow) and `docs/ux/DESIGN.md`.
   - Document the endpoint in `docs/api/applications/README.md` and
     `docs/api/API.md`.

## Testing Requirements

- Backend:
  - Repository counts by status, excludes other users, omits zero counts, and
    reports `total`.
  - Router returns the distribution for the authenticated user and an empty
    payload when there are no applications.
- Frontend:
  - `buildApplicationStatusSlices`: important order, Other fold, percentages
    against the full total, zero/empty safety.
  - Chart renders legend/total/role and empty/loading states.
  - `DashboardPage` renders the new panel and its error/retry state.
  - `applicationApi.statusDistribution` calls the new endpoint.
- Run `./scripts/docker-test.sh backend` and
  `./scripts/docker-test.sh frontend` (AGENTS.md rule 18); then typecheck.

## Constraints

- No cross-context database access: the endpoint stays in the Applications
  context even though the chart is on the Dashboard.
- No new migration (status already persisted).
- Keep existing Dashboard widgets and sources table behavior unchanged.
- Respect AGENTS.md 13 (UX wireframe + Mermaid), 16 (no new events needed for a
  read-only aggregate), 17, and 18.
