# Prompt 213 - Show Recommendation Badge in Job Creation Drawer for Duplicate Jobs

## Objective
When a user tries to create a job that already exists, the duplicate-job error drawer shows a summary card with scores, company, location, etc. but omits the AI recommendation (apply/consider/skip). Add the recommendation to the summary so users can quickly assess whether to revisit the existing job.

## Current State
- Backend `_job_summary()` in `apps/backend/jobs/presentation/api/jobs_v2_router.py:198` builds the duplicate error payload but does not include `recommendation`.
- The `create_job` endpoint (line 106) does not inject `analysis_repo`, so it cannot fetch the recommendation.
- Frontend `JobSummary` type in `apps/frontend/src/entities/job/types.ts:77` lacks a `recommendation` field.
- `JobSummaryCard` in `apps/frontend/src/shared/components/CreateEntityDrawer.tsx:100` renders scores, company, location, visa, employment, salary, work types, and tracking status — but not recommendation.
- `RecommendationBadge` component exists at `apps/frontend/src/features/jobs-v2/components/RecommendationBadge.tsx` and is already used in `JobRow`, `JobDetailDrawer`, and `WorkspaceHeader`.

## Changes

### 1. Backend: `apps/backend/jobs/presentation/api/jobs_v2_router.py`
- Add `analysis_repo: SQLAlchemyJobAnalysisRepository = Depends(get_job_analysis_repo)` to `create_job` endpoint params.
- In the duplicate check block, call `analysis_repo.recommendations_by_job_ids([existing_id])` and pass the result to `_job_summary` as `recommendation=recommendations.get(existing_id)`.
- Add `recommendation: str | None = None` parameter to `_job_summary()` and include `"recommendation": recommendation` in the returned dict.

### 2. Frontend type: `apps/frontend/src/entities/job/types.ts`
- Add `recommendation: string | null` to `JobSummary` interface (after `tracking_status`).

### 3. Frontend component: `apps/frontend/src/shared/components/CreateEntityDrawer.tsx`
- Import `RecommendationBadge` from `@/features/jobs-v2/components/RecommendationBadge`.
- In `JobSummaryCard`, add a `SummaryRow` for "Recommendation" rendering `<RecommendationBadge recommendation={job.recommendation} />` between the Visa and Application rows.

### 4. Backend test: `apps/backend/tests/jobs/presentation/api/test_create_job.py`
- Import `JobAnalysisModel`.
- Add `test_create_duplicate_job_includes_recommendation`: creates a job, inserts a `JobAnalysisModel` with `recommendation="apply"`, re-submits the same URL, asserts `body["error"]["details"]["job"]["recommendation"] == "apply"`.

### 5. Frontend test: `apps/frontend/src/shared/components/CreateEntityDrawer.test.tsx`
- Add `recommendation: 'apply'` to the existing job mock in the "renders a summary" test.
- Assert `screen.getByText('Apply')` is present.
- Add `recommendation: null` to the mock in the "invokes onViewJobDetails" test.

## Testing Requirements
- Backend: `./scripts/docker-test.sh backend`
- Frontend: `./scripts/docker-test.sh frontend`

## Constraints
- Respect AGENTS.md rule 15 (no cross-context FKs).
- No new API routes — reuse existing `analysis_repo.recommendations_by_job_ids`.
