# Prompt 243 - Add a Not applied slice to the Dashboard application status chart

## Objective

Give the Dashboard "Applications by status" doughnut an explicit **Not applied**
slice for tracked applications that have not reached `applied` yet, instead of
hiding them inside the gray **Other statuses** bucket.

## Current State

- `apps/frontend/src/features/dashboard/components/ApplicationStatusChart.tsx`
  builds slices from `GET /api/applications/status-distribution`
  (`ApplicationStatusDistribution` in `apps/frontend/src/entities/application/types.ts`).
- `buildApplicationStatusSlices` (`:38`) keeps five important outcomes
  (`applied`, `interview`, `offer`, `accepted`, `rejected`) and folds every
  remaining status (`seen`, `preparing`, `ready_to_apply`, `withdrawn`,
  `expired`) into one gray `Other statuses` slice.
- Pre-application statuses are documented in
  `docs/domain/applications/application.md:24-26` (`seen`, `preparing`,
  `ready_to_apply`).
- Spec: `docs/ux/features/dashboard/page.md` (`## Application status chart`,
  `:114-127`) and `docs/ux/DESIGN.md:912-928`.

## Changes

1. `ApplicationStatusChart.tsx`
   - Add `PRE_APPLICATION_STATUSES = ['seen', 'preparing', 'ready_to_apply']` and
     a fixed amber `NOT_APPLIED_COLOR`.
   - In `buildApplicationStatusSlices`, emit a single `Not applied` slice
     (key `not_applied`) built from those statuses, before `Applied`; keep the
     five important outcomes in fixed order and keep `Other statuses` for the
     remaining terminal statuses (`withdrawn`, `expired`) only.
   - Percentages still use the full application `total` as denominator; hide the
     slice when its count is zero.
2. Tests in `apps/frontend/src/features/dashboard/components/Dashboard.test.tsx`
   - Update the slice-order expectation, verify `Not applied` aggregates all
     three pre-application statuses, and that `Other statuses` only keeps the
     terminal leftovers. Render test asserts the new legend entry.
3. Docs
   - `docs/ux/features/dashboard/page.md`: layout tree, wireframe, chart rules.
   - `docs/ux/DESIGN.md`: Dashboard wireframe + prose.
   - `docs/api/applications/README.md`: note that the aggregate feeds the
     Not applied slice (endpoint payload unchanged).

## Testing Requirements

- `./scripts/docker-test.sh frontend` (AGENTS.md rule 18).
- `cd apps/frontend && npm run lint && npm run typecheck`.

## Constraints

- Frontend-only change; no API, schema, migration or event changes.
- Keep the other Dashboard widgets untouched.
- Respect AGENTS.md 13 (wireframe docs), 17, 18.
