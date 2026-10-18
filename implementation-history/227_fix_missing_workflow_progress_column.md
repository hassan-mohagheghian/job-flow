# Prompt 227 - Fix: missing `workflow_progress` column → 500 on `/api/candidates/analyze`

## Objective

`POST /api/candidates/analyze` returns **500**. Restore a trustworthy Alembic state on the dev DB and create the missing `processing.processing_executions.workflow_progress` column through a proper per-context migration, so the endpoint works and the deploy-time `job-search-alembic` one-shot stops failing with `DuplicateTable`.

## Current State (evidence)

- Backend log (`docker logs job-search-backend`):
  `sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedColumn) column processing.processing_executions.workflow_progress does not exist`
  raised from `candidates/presentation/api/candidates_router.py:135` →
  `create_processing_execution.py:37` → `sa_processing_execution_repository.py:149`.
- `docker exec job-search-postgres psql ... -c "select ... information_schema.tables where table_name ilike '%alembic%'"` → **0 rows**: this DB has **no `alembic_version` table at all** (`alembic current` prints no revision).
- `docker logs job-search-alembic` → **Exited (1)**: `DuplicateTable relation "rules" already exists` (exactly the scenario of `implementation-history/192_fix_alembic_single_head.md`).
- `apps/alembic/versions/025_add_workflow_progress.py` lives in the **legacy single dir**, which `alembic.ini:6 version_locations` does **not** scan (AGENTS.md rule 14 "Placement"). Its `down_revision = '024_add_uuid_v7_to_jobs'` is also stranded, so relocating the file would create a broken/cross-linked branch — **do not relocate it**.
- Legacy `026_add_companies_raw_content.py` is a *duplicate* of `apps/alembic/company/versions/company_003_add_companies_raw_content.py` (already applied — `company.companies.raw_content` exists).
- Model-vs-DB drift (read-only script, `Base.metadata` vs `inspect(engine)` over all 50 tables):
  - missing: `processing.processing_executions.workflow_progress` ← the only real gap
  - DB-only: `company.companies.links`, `company.company_links.updated_at` (harmless leftovers, not modeled)
- `uv run alembic heads` → exactly one head `job_009`; `alembic history -r base:heads` resolves.

## Implementation Steps

1. `uv run alembic stamp head` on the dev DB — creates `alembic_version` stamped at `job_009` without re-running anything (precedent: `implementation-history/192_fix_alembic_single_head.md` step 3). Non-destructive.
2. Autogenerate the real fix (rule 14 — never hand-write the revision graph):
   `ALEMBIC_TARGET_SCHEMA=processing uv run alembic revision --autogenerate -m "add workflow_progress to processing_executions" --version-path apps/alembic/processing/versions`
   → inspect the generated file; tune **content** only (must be a single `op.add_column(..., schema="processing")` + matching `downgrade`; no table drops, no cross-context FKs).
3. Verify `uv run alembic heads` (single head) + `uv run alembic history -r base:heads`.
4. `uv run alembic upgrade head` → applies only the new revision; then downgrade/upgrade round-trip (rule 14).
5. Re-run the drift script → `(none)` for missing columns.
6. Smoke: `POST /api/candidates/analyze` → 202 (or 200 `noop`), no `UndefinedColumn`.

## Testing Requirements

- `./scripts/docker-test.sh all` green before any `start terraform up` (rule 18).
- `uv run alembic heads` → one head; `alembic current` shows the new revision on the dev DB.
- Drift script reports no missing tables/columns.
- Endpoint smoke test returns non-500.

## Constraints

- AGENTS.md rules 14 (per-context placement, autogenerate-first, single head, fresh-DB verify, downgrade/upgrade round-trip), 18 (tests in Docker; `start terraform test all` before `start terraform up`), 16, 17.
- No cross-context FKs; no `print()`; no version bump (bug fix + migration, not a release).
- Do **not** relocate or delete the stranded legacy files in `apps/alembic/versions/` in this change (their effects are already in the DB; re-running them would fail) — flag as follow-up.
- Preserve the pre-existing uncommitted worktree edits from prompt 226.
- Caveat to state plainly: `stamp head` assumes non-schema (data) migrations already ran; schema-level drift was measured and is empty apart from `workflow_progress`.
