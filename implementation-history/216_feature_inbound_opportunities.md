# Prompt 216 - Inbound Opportunities Pipeline

## Objective
Add a manual inbound-opportunity workflow that turns pasted recruiter/message text into a structured, progressively enrichable Opportunity, reusing candidate context, rules, scoring, and entity resolution. Keep the existing JD-first system unchanged.

## Current State
- Applications pattern: aggregate/service/router/schemas at `apps/backend/applications/domain/entities/application.py:84`, `application/services/application_service.py:20`, `presentation/api/applications_router.py:143`, `presentation/api/schemas/applications.py:108`; registered at `shared/presentation/api/root_router.py:56`.
- DI: `dependencies.py:158` wires application repos/services; tests use `apps/backend/tests/conftest.py:111` with `test-user`.
- Candidate truth: `ICandidateProfileRepository.get_current_profile` (`candidates/domain/repositories/candidate_profile_repository.py:22`); prompt builders in `processing/application/services/job_analysis_inputs.py:52`; rules via `get_enabled_by_scopes` (`rules/infrastructure/repositories/sa_rule_repository.py:43`).
- Deterministic scoring: overall/recommendation helpers in `processing/application/services/job_analysis_scoring.py:36`; LLM entry `LLMService.generate_structured` (`ai/infrastructure/service.py:84`).
- Resolution reuse: job URL duplicates in `jobs/domain/services/job_url_rules.py:69`; company match helpers in `companies/application/services/company_matching_service.py:76`; skill exact lookup in `skills/infrastructure/repositories/sa_skill_repository.py:279` (`resolve_skill` at `:542` auto-creates, so do not use it here).
- Frontend: route pattern `apps/frontend/app/jobs/page.tsx:1`; widget wiring `src/widgets/jobs-page-v2/index.tsx:23`; API client `src/entities/job/api.ts:29`; nav `src/widgets/sidebar/nav-items.ts:26`; nav tests `src/widgets/sidebar/Sidebar.test.tsx:44`.
- Migrations: generate-first workflow in `docs/database/alembic-guide.md:52`; new schema/model registration via `apps/alembic/env.py:30` and `sqlalchemy_config.py:29`.

## Changes
1. New `opportunities` context plus `opportunity` schema: `opportunities` root with source/message metadata, `raw_content`, URL/content hashes, extracted JSON, logical `company_id`/`job_id`, nullable fit/success/overall, recommendation, evaluation JSON, path/next action, status; child `opportunity_evaluations` snapshots for history. No cross-schema FKs.
2. Domain events/publisher/catalog: created/extracted/linked/evaluated/status-changed via in-memory collector; add `docs/domain/opportunities/events.md`.
3. `OpportunityService`: create from manual input; extract partial fields with explicit `known/unknown/inferred/needs_verification`; dedupe by source-message ID/content hash/duplicate job URL; link existing job/company only on confident matches; reprocess re-extracts, re-resolves, re-evaluates and appends evaluation history.
4. Versioned `opportunity.extract` and `opportunity.evaluate` prompts; evaluation consumes canonical candidate text plus SHARED/JOB rules and linked job/company; deterministic overall/recommendation reuse; insufficient information yields pending evaluation, missing-info list, and research next action without invented scores/URLs.
5. Endpoints under `/api/opportunities`: create/list/detail/reprocess/link/status; register router and dependencies following applications conventions.
6. Frontend `/opportunities`: entity API/types, page widget/list/detail drawer/create flow, sidebar entry; reuse table/drawer/toolbar primitives and newest-first ordering.

## Testing Requirements
- Backend red tests: service extraction/evaluation/dedupe/linking/scoring, repository persistence/history, API create/detail/reprocess/status.
- Frontend red tests: entity API, list/detail/create flows, nav entry, optimistic updates.
- Run `./scripts/docker-test.sh all`; frontend `npm run lint` and `npm run typecheck`; generate/tune/verify the Alembic migration before implementation completes.

## Constraints
- Respect AGENTS.md rules 1, 2, 3, 10, 11, 13, 14, 15, 16, 18.
- Reuse existing scoring/candidate/rules/matching logic; no parallel candidate/job systems, no fabricated fields/URLs/scores, no provider-direct AI calls, no background/SSE infrastructure in phase one.
