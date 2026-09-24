# Prompt 214 - Move Pin into Drawers, Remove Pin Column from Lists

## Objective
Move the pin toggle out of the job/company/skill list tables and into each entity's detail drawer header, so the lists drop the Pin column while pinning stays a one-click action with the same optimistic UX. Relevant for all three job/company/skill lists. The toolbar "Pinned" filter is retained — only the column is removed.

## Current State
- Pin column + row PinButton exist in `JobsTable.tsx`/`JobRow.tsx` (`PIN_COLUMN`, `showPinnedColumn`), `CompaniesTable.tsx`/`CompanyRow.tsx`, `SkillsTable.tsx`/`SkillRow.tsx`; grid helpers `jobsColumns.ts`/`companiesColumns.ts`/`skillsColumns.ts` prepend `LEADING_COLUMN_WIDTH` (`44px`) for the pin column.
- Toolbars (`JobsToolbar.tsx`, `CompaniesToolbar.tsx`, `SkillsToolbar.tsx`) have a `showPinnedColumn`/`onTogglePinnedColumn` ColumnsDropdown entry plus a retained pinned *filter* (`filterPinned`).
- Widgets (`widgets/jobs-page-v2`, `widgets/companies-page`, `widgets/skills-page`) hold `showPinnedColumn` state and `handleTogglePinned`; jobs handler is `(id: string) => void` deriving flipped state from list items (`widgets/jobs-page-v2/index.tsx:130-134`), companies/skills are `(id, pinned)`.
- Detail drawers have no pin: `JobDetailDrawer.tsx` (header actions L794-830: Reprocess/Application/Edit; fetches its own `["job-detail", jobId]`), `CompanyDetailDrawer.tsx` (header L217-242: Reprocess/Edit; `useCompanyQuery`), `SkillDetailDrawer.tsx` (header action Edit; receives `skill: SkillListItem` prop).
- Backend detail responses lack `pinned`: `JobDetailResponseSchema` (`apps/backend/jobs/presentation/api/schemas/jobs_v2.py:251`, built at `_job_detail_payload` L535 and inline GET L625), `CompanyDetailResponseSchema` (`companies_v2.py:151`, built at `_build_company_detail` L472). Mappers/repos already include `pinned` in `get_by_id` dicts (jobs mapper L63, company mapper L56).
- Skill detail already exposes `pinned`; the drawer uses the list item.
- Shared `PinButton` exists at `apps/frontend/src/shared/components/PinButton.tsx` (icon-only, `h-6 w-6`).
- Known bug: company `pinnedMutation` rollback passes the `getQueriesData` entries array directly to `setQueriesData` (`entities/company/hooks.ts:147`); jobs/skills iterate entries correctly. Company mutation also has no `onSettled`.

## Changes

### 1. Backend: expose `pinned` in job + company detail
- `jobs/presentation/api/schemas/jobs_v2.py`: add `pinned: bool = False` to `JobDetailResponseSchema`.
- `jobs/presentation/api/jobs_v2_router.py`: add `pinned=bool(job_dict.get("pinned"))` in `_job_detail_payload` (L535) and inline `get_job_detail` (L625).
- `companies/presentation/api/schemas/companies_v2.py`: add `pinned: bool = False` to `CompanyDetailResponseSchema`.
- `companies/presentation/api/companies_v2_router.py`: add `pinned=bool(company.get("pinned"))` in `_build_company_detail` (L472).

### 2. Frontend types + mutations
- `entities/job/types.ts`: `pinned?: boolean` on `JobDetail`.
- `entities/company/types.ts`: `pinned?: boolean` on `CompanyDetail`.
- `shared/components/PinButton.tsx`: optional `className` merged via `cn`.
- `features/jobs-v2/hooks/useJobsInfiniteQuery.ts` `pinnedMutation` (L185): optimistically patch `["job-detail", jobId]` in `onMutate` (snapshot for rollback), invalidate it in `onSettled`.
- `entities/company/hooks.ts` `pinnedMutation` (L124): patch `["company-detail", id]`, fix rollback to iterate entries (jobs pattern), add `onSettled` invalidate of `COMPANIES_KEY` + `COMPANY_DETAIL_KEY`.
- `widgets/jobs-page-v2/index.tsx`: `handleTogglePinned` → `(id: string, pinned: boolean) => pinnedMutation.mutate({ jobId: id, pinned })`.
- `features/jobs-v2/components/JobsPage.tsx`: `onTogglePinned` prop type → `(id: string, pinned: boolean) => void`.

### 3. Drawers: PinButton in header actions
- Add optional `onTogglePinned?: (id, pinned) => void` to `JobDetailDrawer.tsx`, `CompanyDetailDrawer.tsx`, `SkillDetailDrawer.tsx` props; render shared `PinButton` first in the header actions when the prop is present; state from `detail?.pinned` / `company?.pinned` / `skill.pinned`. (Avoid the unrelated local `pinned` scores-popover state in `CompanyDetailContent`.)
- Pass the prop from `JobsPage.tsx` (L224), `CompaniesPage.tsx` (L180), `SkillsPage.tsx` (L260) instead of to the tables.

### 4. Lists: remove pin column
For jobs, companies, skills:
- Tables (`JobsTable.tsx`, `CompaniesTable.tsx`, `SkillsTable.tsx`) and rows (`JobRow.tsx`, `CompanyRow.tsx`, `SkillRow.tsx`): drop `PIN_COLUMN`, `showPinnedColumn`, pin cell, `onTogglePinned` row wiring.
- Column helpers: drop `showPinned` param from `buildJobGridTemplate`/`buildCompanyGridTemplate`/`buildSkillGridTemplate` (keep `LEADING_COLUMN_WIDTH` for `#`/select columns).
- Toolbars: remove `showPinnedColumn`/`onTogglePinnedColumn` props + "Pinned" ColumnsDropdown entry; keep the pinned filter button.
- Pages + widgets: remove column props/state; keep `handleTogglePinned` (now feeds drawers).

### 5. Tests (red first)
- Backend: add detail-carries-`pinned` tests to `TestJobPinnedV2API` (`apps/backend/tests/jobs/presentation/api/test_jobs_v2_api.py`) and company equivalent (`apps/backend/tests/companies/presentation/api/test_companies_v2_api.py`).
- Frontend: remove pin row/column tests from `JobRow.test.tsx`, `CompanyRow.test.tsx`, `SkillRow.test.tsx`, `JobsToolbar.test.tsx` (L190-220), `CompaniesToolbar.test.tsx` (L150-180), `SkillsPage.test.tsx` (L165-192); keep pinned-filter tests.
- Add drawer pin tests: `JobDetailDrawer.test.tsx`, `CompanyDetailDrawer.test.tsx`, `SkillDetailDrawer.test.tsx` (aria state, click toggles via `onTogglePinned(id, !pinned)`, hidden when prop absent).
- Extend `useJobsInfiniteQuery.test.tsx` optimistic-toggle test (L499-557) to assert the `["job-detail", jobId]` patch + rollback.

## Testing Requirements
- `./scripts/docker-test.sh all`
- Frontend: `npm run lint` + `npm run typecheck` (apps/frontend)
- No Alembic run — no model changes.

## Constraints
- Respect AGENTS.md rule 13 (UX docs with ASCII wireframes + Mermaid for flows), rule 14/15 (no migration, no cross-context FKs), rule 18 (Docker tests only).
- Docs to update: UX `pinned-job.md`, `page.md` ×3, `job-row.md`, `company-detail.md`, `skill-detail.md`, `DESIGN.md`, `README.md`; API `API.md`, `list-jobs.md`, `company-detail.md`; domain `overview.md`.
- Keep the pinned filter behavior untouched.
- No pin in `ApplicationWorkspace`/`GlobalAddJobProvider` job-drawer mounts (no handler there; optional prop stays unset).