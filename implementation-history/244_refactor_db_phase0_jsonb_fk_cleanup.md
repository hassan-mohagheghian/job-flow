# Prompt 244 - Jobs table phase 0: JSONB arrays, intra-context FKs, dead-column cleanup

## Objective

Make the `job` schema honest before considering any further normalization:
remove dead/duplicated columns, store the filtered multi-valued fields as real
JSONB (indexable, query-correct), enforce same-context referential integrity
with FKs, and stop list queries from loading multi-KB text payloads. No API
contract changes; the frontend keeps receiving `work_types` /
`employment_types` / `tags` as string arrays.

## Current State

- `jobs` has 60 columns (`apps/backend/jobs/infrastructure/models/job_model.py:17`).
  `match`, `score`, `success`, `locations` are 100% NULL / empty in the live DB
  (126 rows), yet `filter_matches`, `filter_scores`, `filter_cities`,
  `get_stats`, `get_dashboard_counts` still query them
  (`apps/backend/jobs/infrastructure/repositories/sa_job_repository.py:107-206,803`).
- `work_types`, `employment_types`, `tags` are `Text` JSON arrays. Filters use
  `LIKE '%"value"%'` (`contains(f'"{x}"')`), which cannot use an index and is
  substring-fragile. `tags` is documented as Text in
  `docs/ux/features/jobs/job-tags.md:88`.
- `job_analysis.job_id` and `summaries.job_id` have no FK to `job.jobs`
  (3 orphan rows each exist in the dev DB). `job_companies` already models the
  correct same-context FK + CASCADE pattern
  (`apps/backend/jobs/infrastructure/models/job_company_model.py:27`).
- `search_jobs_cursor` loads whole `JobModel` rows including
  `raw_description` / `description` / `structured_description` (~6 KB each)
  for a list projection of ~15 fields
  (`apps/backend/jobs/infrastructure/repositories/sa_job_repository.py:925`).
- `jobs` has separate single-column `user_id` and `created_at` indexes; the
  base query filters `(user_id, deleted)` and sorts `created_at`.
- `match` / `score` surface in the company-detail job projection
  (`apps/backend/companies/presentation/api/companies_v2_router.py:399,460` and
  `schemas/companies_v2.py:111`) and in the unused legacy `Job` frontend type
  (`apps/frontend/src/entities/job/types.ts:1`).

## Changes

1. **Model (`job_model.py`)** — drop `match`, `score`, `success`, `locations`;
   change `work_types`, `employment_types`, `tags` to `JSONB` non-null with
   list defaults (`[]`, `["Full-time"]`, `[]`); add GIN indexes on the three
   JSONB columns and a composite `(user_id, deleted, created_at)` index in
   `__table_args__`.
2. **Model (`job_analysis_model.py`, `misc_models.py`)** — add same-schema
   `ForeignKey("job.jobs.id", ondelete="CASCADE")` to
   `job_analysis.job_id` and `summaries.job_id`.
3. **Mapper (`jobs/infrastructure/mappers.py`)** — remove dropped keys; add a
   list projection mapper used by the cursor list query.
4. **Repository (`sa_job_repository.py`)** —
   - JSONB containment filters (`work_types`, `employment_types`, `tags`),
     including the negated remote branch;
   - `filter_cities` uses `location` only; remove `filter_matches` /
     `filter_scores` / `get_stats`; `get_dashboard_counts` derives
     `jobs_high_match` from `overall_score >= 80`;
   - remove legacy score sort keys; `set_tags` writes a list;
   - `search_jobs_cursor` loads only list fields and maps with the new list
     mapper; `get_location_data` no longer selects `locations`.
5. **Domain entity (`jobs/domain/entities/job.py`)** — remove dropped fields,
   type the three arrays as `list[str]`, update `to_dict` / `from_dict`.
6. **Writers** — `processing/.../persist_node.py`, legacy
   `jobs/infrastructure/workers/worker.py`, `shared/infrastructure/process/repository.py`,
   API update route (stop `json.dumps` for work/employment types),
   `jobs/application/commands/normalize_locations.py`: write Python lists, drop
   `locations` DB writes. `notes` / `links` / `workflow_log` stay `Text`.
7. **Company projection** — drop `match` / `score` from
   `CompanyJobRefSchema`, the two router mappings and the docs example.
8. **Frontend** — remove `match`, `score`, `locations` from the unused legacy
   `Job` interface shape (`jobs_v2` types untouched).
9. **Migration** — autogenerate from the current head `807af848eab4` with
   `ALEMBIC_TARGET_SCHEMA=job`, then tune: `CREATE SCHEMA IF NOT EXISTS job`,
   guard every drop/add/index/FK with the inspector, delete orphan
   `job_analysis` / `summaries` rows before adding FKs, convert Text→JSONB with
   a safe `USING` cast, and a reversible downgrade. Single head afterwards.
10. **Docs** — `docs/database/sqlalchemy-architecture.md` (storage decisions,
    FKs, indexes), `docs/ux/features/jobs/job-tags.md` (JSONB, still no tags
    table), `docs/api/companies/company-detail.md` (no match/score).

## Testing Requirements

- Update repository tests to use list values and JSONB filters
  (`test_sa_repositories.py`, `test_sa_job_repository_extra.py`); delete the
  `filter_matches` / `filter_scores` / `get_stats` tests.
- Update fixtures that pass JSON strings (`test_jobs_v2_*.py`,
  `test_integration_jobs.py`, `test_process_job.py`,
  `test_applications_router.py`, `test_jobs_sources_api.py`) to lists and
  remove `locations`.
- Update worker tests that `json.loads` the ORM column to assert lists.
- Add: JSONB containment false-positive guard (`"Remote"` must not match
  `"Remote Work"`), tags intersection round-trip, cascade delete removes
  `job_analysis` + `summaries`, dashboard high-match derives from
  `overall_score`.
- Run `./scripts/docker-test.sh backend` and
  `./scripts/docker-test.sh frontend` plus `npm run lint && npm run typecheck`.
- Verify migration with `uv run alembic heads` (one head),
  `uv run alembic history -r base:heads`, fresh-DB `upgrade head`, and a
  downgrade/upgrade round-trip.

## Constraints

- No cross-context FKs (AGENTS.md rule 15); only `job` schema FKs.
- Autogenerated revision graph only; tune content, never hand-write
  `revision` / `down_revision`.
- No API shape change: arrays stay arrays; removed fields were always null.
- No new dependencies; SQLAlchemy ORM only (no raw SQL in application code;
  migration DDL is fine).
- `notes`, `links`, `workflow_log`, `raw_description`, `structured_description`
  remain `Text` in this phase.
