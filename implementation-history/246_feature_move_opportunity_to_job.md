# Prompt 246 - Feature: Move Opportunity to Job (manual conversion)

## Objective

Give the user an explicit action to **move an evaluated, scored opportunity into
the Jobs bounded context**. A manual "Move to Jobs" action on an opportunity
whose evaluation is complete (`evaluation_status=complete` with an overall
score) either links the existing matching job or creates a new job row that
carries the opportunity's three scores, the raw inbound message as the JD note,
and the extracted role/company context. After the move the opportunity stays in
the funnel, marked as linked (`job_id` / `job_title` set).

Decisions (confirmed with the user):

- **Trigger: manual only.** No auto-conversion inside `_evaluate()`.
- **Create-or-link by URL.** If a matching job already exists, only link it;
  otherwise create the job from the extracted URL + role title.
- **Job content consistency.** The created job must be consistent with the
  opportunity's extracted/evaluated state: copy `fit_score`, `success_score`,
  `overall_score` (the 3 scores), store the raw inbound message as the job's
  JD note, set `role`/`title` and `company` from extracted data, and set
  `company_id` when the opportunity has one.
- **After the move:** keep the funnel status; only `job_id`/`job_title` change.
- **No queueing.** The created job stays in status `imported`; the user can run
  the full AI pipeline from the Jobs page later.

## Current state

- `apps/backend/opportunities/application/services/opportunity_service.py` —
  `OpportunityService` has `job_repo` injected; `_resolve_job()` only *links*
  existing rows; the context "never creates jobs" is stated in the module and
  entity docstrings and in `docs/domain/opportunities/opportunity.md`.
- `apps/backend/jobs/infrastructure/repositories/sa_job_repository.py` —
  `create_job(url, title, notes, links, source)` (status `imported`) and
  `update_fields(item_id, **fields)` already exist; no jobs-context changes
  needed.
- `apps/backend/jobs/domain/services/job_url_rules.py` — `find_duplicate_job()`
  is the URL dedupe rule used by the jobs create endpoint.
- Jobs notes are a JSON list of `{content, title?}` items
  (`jobs/presentation/api/schemas/jobs_v2.py:JobNoteItem`).
- Domain events (rule 16): `apps/backend/opportunities/domain/events.py`
  documents+defining pattern; catalog at `docs/domain/opportunities/events.md`.
- API: `POST /api/opportunities/{opportunity_id}/move-to-job` does not exist
  (router `apps/backend/opportunities/presentation/api/opportunities_router.py`).
- Frontend (FSD): `entities/opportunity/api.ts` (+ `hooks.ts`), feature
  `features/opportunities/components/OpportunityDetailDrawer.tsx` — no convert
  action yet.

## Implementation steps

1. **Backend domain**: add frozen event `OpportunityMovedToJob`
   (`event_type="opportunity.moved_to_job"`, payload: `opportunity_id`,
   `job_id`, `job_title`, `overall_score`, `recommendation`, `created_job`.
   Export it from `events.py` and document it in
   `docs/domain/opportunities/events.md`.
2. **Backend service**: `OpportunityService.move_to_job(opportunity_id)`:
   - Raise `ValidationError` when the opportunity's evaluation is not complete
     or has no overall score.
   - Idempotent: if `job_id` is already set, just return the presented detail.
   - Pick the best extracted job URL; raise `ValidationError` when none.
   - `find_duplicate_job(self._jobs, url)` → link existing job, else
     `self._jobs.create_job(url, title, notes=<raw message note>,
     source="opportunity")` then `update_fields(...)` to copy the 3 scores,
     company link and role context. Best-effort: job creation/update must not
     hard-fail the opportunity update once the job exists.
   - Update the opportunity (`job_id`, `job_title`, `updated_at`) and emit
     `OpportunityMovedToJob`.
   - Return the detail (plus the resulting job summary, `created_job` flag).
   - Lift the "never creates jobs" docstrings to reflect the explicit,
     deliberate exception (only this action creates a job).
3. **Backend API**: `POST /{id}/move-to-job` in `opportunities_router.py`
   (per-context router — rule 10); schema for the response. Map
   `OpportunityPipelineError` → 502 like the process endpoints.
4. **Frontend**: `entities/opportunity/api.ts` `moveToJob`, React Query hook
   invalidating `['opportunities']` and `['jobs']` query keys; wireframe-consistent
   button "Move to Jobs" in `OpportunityDetailDrawer` (disabled until
   `evaluation_status === 'complete'`; hidden/neutral once `job_id` is set,
   with a link to the job in Jobs).
5. **Docs**: domain (`docs/domain/opportunities/opportunity.md`, events.md,
   `docs/domain/overview.md` sync), API (`docs/api/opportunities/README.md`,
   `docs/api/API.md`), UX (opportunity-detail wireframe + flow + `README.md`
   + `DESIGN.md` — ASCII + Mermaid per rule 13).

## Testing requirements

- Backend: extend
  `apps/backend/tests/opportunities/domain/test_opportunity_service.py`
  (FakeJobRepo gains `create_job`/`update_fields`): create-path, link-path,
  idempotent re-move, validation on unevaluated/missing-URL, event emitted.
  Router test in
  `apps/backend/tests/opportunities/presentation/api/test_opportunities_router.py`.
- Frontend: vitest API test for `moveToJob`.
- Run via Docker only (rule 18): `./scripts/docker-test.sh backend|frontend`.

## Constraints

- No cross-context FK (rule 15) — `job_id` stays a plain logical column.
- Event is best-effort, emitted by the service performing the change; no
  pub/sub infra (rule 16).
- No DB migration needed (no schema change).
- AI calls stay through LLMService (none added); no `print()` (structlog).
- Version bump not required until release time.
