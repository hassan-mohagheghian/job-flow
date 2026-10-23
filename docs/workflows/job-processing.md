# Job Processing Workflow

## Purpose

This document describes the workflow responsible for processing jobs.

The workflow analyzes job information, extracts relevant data, uses AI providers, and generates scoring and career guidance.

---

# Architecture Flow

Job

↓

ProcessingExecution

↓

TaskIQ Worker

↓

LangGraph Workflow

↓

Processing Nodes

↓

Result

---

# Workflow Responsibilities

The job processing workflow is responsible for:

- Collecting job information
- Extracting structured data
- Running AI analysis
- Generating job score
- Generating career guidance
- Persisting final results

---

# Workflow Graph

A job processing run executes two LangGraph phases inside a single
ProcessingExecution.

## Phase 1 — Context Preparation

`processing/application/workflows/job_context_preparation/graph.py`

START

↓

load_job

↓

collect_sources

↓

fetch_sources

↓

extract_content

↓

build_context

↓

validate_context

↓

persist_context

↓

context_ready | execution_failed

No LLM calls. `persist_context` writes the combined text to the job row
(`raw_description` + `description`) via `JobService.persist_prepared_context`,
so the analysis phase has a durable LLM input.

## Phase 2 — Job Analysis

`processing/application/workflows/job_analysis/graph.py`

load_context

↓

prepare_profile

↓

analyze

↓

extract_skills

↓

score

↓

recommend

↓

summarize

↓

persist

↓

persist_skills

↓

link_company

↓

analysis_ready | execution_failed

Exactly ONE LLM call: `analyze` runs the `job.analyze` prompt via
`LLMService.generate_structured(prompt, schema=…, timeout=240)`.

END

If Phase 1 ends with `execution_failed`, the execution fails and Phase 2 is
skipped.

---

# Node Description

## Phase 1 — Context Preparation

## load_job

Loads job information from the domain layer.

Input:

- job_id
- execution_id

Output:

- job context

On failure the execution is marked failed with the `[load_job]` prefix.

---

## collect_sources

Collects the source list for the job (primary URL, reference URLs, notes).

Output:

- source list

---

## fetch_sources

Retrieves external content for each source.

Examples:

- Company website
- External resources
- Job descriptions

Handled by `CompositeContentFetcher` (`HTTPXContentFetcher`,
`PlaywrightContentFetcher`).

Output:

- External content

---

## extract_content

Transforms raw content into structured text.

Handled by `CompositeContentExtractor` (`TrafilaturaContentExtractor`,
`BeautifulSoupContentExtractor`). The extractors decompose non-content
elements (script/style/head/noscript/iframe/template/svg) so inline JS and
Next.js RSC payloads never leak into the LLM context. When no extractor
produces clean text, the composite falls back to a best-effort
markup-stripped passthrough that also removes those element bodies and caps
the result at `MAX_FALLBACK_CHARS` (40 000) in
`processing/infrastructure/content/extractors/__init__.py`.

Output:

- Cleaned content per source

---

## build_context

Combines the extracted content into a single `combined_text` processing
context.

The context is trimmed to the prompt budget via
`processing/application/services/context_budget.py`:

- each extracted source is trimmed to `MAX_SOURCE_CHARS` (8 000) so a single
  oversized page cannot crowd out the others
- the combined text is trimmed to `MAX_COMBINED_CHARS` (48 000) so the total
  prompt stays inside the provider output window (oversized inputs make the
  small models truncate or malform the response JSON)

Truncated text keeps its head and ends with a `[truncated]` marker.

Output:

- processing context

---

## validate_context

Validates the combined context is usable.

On success routes to `persist_context`; on failure routes to
`execution_failed`.

Reasons surfaced from validation are each prefixed with `[validate_context]`.

---

## persist_context

Persists the combined text to the job row (`raw_description` +
`description`) via `JobService.persist_prepared_context`. This gives the
analysis phase a durable LLM input.

No LLM call.

---

## context_ready

Marks Phase 1 complete. Internal node — not exposed to the frontend.

---

## execution_failed

Marks the execution failed. Internal node — not exposed to the frontend.

---

## Phase 2 — Job Analysis

## load_context

Loads the persisted job context (the combined text written by
`persist_context`) plus the analysis context. Internal node — not exposed to
the frontend.

---

## prepare_profile

Builds the user profile inputs (skills, latest resume, latest LinkedIn,
scoring rules) used by the analysis prompt. The latest resume (`original_*`)
and latest LinkedIn profile (`linkedin_*`) — each the highest `version` row —
are passed as labeled profile-documents sections into the prompt; the resume is
authoritative for skills/seniority and LinkedIn supplements it. Internal node —
not exposed to the frontend.

---

## analyze

Runs the single combined LLM call: the versioned `job.analyze` prompt via
`LLMService.generate_structured(prompt, schema=…, timeout=240)`. Exactly one
LLM call per job (plus one retry on a parse/schema failure).

Strict schema validation:

- The response is validated against `JobAnalysisOutput`
  (`processing/application/services/job_analysis_validation.py`) before it is
  accepted. All required fields must be present and correctly typed (`scores`
  with `fit`/`success`, `recommendation`, `apply_reason`, `summary`, `skills`,
  `insights`).
- On a JSON parse failure or a `ValidationError`, the call is retried once with
  a shorter-output directive.
- A schema-shaped response
  (`{"type": "object", "properties": {<fields>}}`) is unwrapped by
  `ai/infrastructure/parsers.py::unwrap_schema_echo` before validation, and a
  payload with no `title`/`company`/`location`/`role`/`description` is treated
  as a format failure so the retry can fill the fields.
- If the retry also fails validation, the step fails with the clean message
  "The AI returned an analysis that does not match the required format." and
  nothing is persisted — only schema-valid output ever reaches the database.

Output:

- Structured analysis payload (job fields, scores, recommendation, summary,
  skills, insights)
- A `companies` block with an optional `hiring_company` and a list of
  `related_companies` (recruiter / staffing / consulting agencies). Each
  company reference carries `name`, `company_type` (`hiring`, `recruiter`,
  `staffing`, `consulting`, `outsourcing`, `unknown`), `confidence` and a
  `reason`. The `hiring_company` is never guessed — it is omitted when the
  evidence is weak.

---

## extract_skills

Normalizes the LLM skills list and tags each skill `matched`, `missing`, or
`low` (`normalize_skills`).

---

## score

Deterministic scoring (pure helpers in
`processing/application/services/job_analysis_scoring.py`):

- Scores clamped 0-100
- `overall = round(fit * 0.6 + success * 0.4)`
- Recommendation: `apply` ≥ 80, `consider` ≥ 60, else `skip`

---

## recommend

Derives the recommendation from the overall score.

---

## summarize

Builds the summary block (summary, resume fit, note).

---

## persist

Writes results to three places:

- the `jobs` row projection (fields + apply_reason + scores)
- the `summaries` row (legacy grade via `grade_for_overall`)
- the canonical `job_analysis` table (schema `job`) via
  `SQLAlchemyJobAnalysisRepository.upsert_by_job_id`

---

## persist_skills

Persists the normalized skills list and the per-skill match status.

---

## link_company

Best-effort company resolution for the extracted `companies` block. Never fails
the execution — a resolution error is appended to `state.errors` and the
workflow continues.

1. **Hiring company** — when a `hiring_company` with a non-empty `name` was
   extracted, `CompanyMatchingService.find_or_create(name, company_url,
   company_type)` resolves or creates it and `jobs.company_id` /
   `jobs.company` are updated. The extraction `company_type` is mapped to the
   companies vocabulary (`hiring → PRODUCT_COMPANY`, `recruiter →
   RECRUITING_AGENCY`, `staffing → STAFFING_COMPANY`, `consulting →
   CONSULTING_COMPANY`, else `UNKNOWN`) and stored **only** on newly-created
   companies — matching an existing company never mutates it.
2. **Related companies** — each `related_companies` reference is resolved or
   created with `role="recruiter"`.
3. **Persist** — all resolved associations are written to the `job_companies`
   table (schema `job`) as rows (`role` `hiring` or `recruiter`, `company_type`,
   `confidence`, `reason`). Rows are **replaced** for the job on every
   re-process (`replace_for_job`).
4. **Fallback display** — when no hiring company was extracted but a related
   (publishing) company exists, `jobs.company` falls back to the
   highest-confidence related company so the job still has a display name.

---

## analysis_ready

Marks Phase 2 complete. Internal node — not exposed to the frontend.

---

# Workflow State

Workflow state contains:

- Job context
- Extracted information
- Analysis results
- LLM responses
- Generated insights

Workflow state is managed by LangGraph.

---

# ProcessingExecution Integration

Each workflow execution belongs to a ProcessingExecution.

ProcessingExecution tracks:

- Status
- Lifecycle
- Failure state

LangGraph tracks:

- Workflow progress
- Node execution
- Checkpoints

---

# Failure Handling

## Error Message Format

Every user-facing error emitted by a workflow step is prefixed with the
step that produced it, in the form:

```
[step] message
```

Example:

```
[load_job] Failed to parse job data: ...
[fetch_sources] Fetch failed: https://example.com/a: ...
[validate_context] No usable content source was collected.
[persist_context] No combined text to persist for {job_id}
[analyze] Failed to run job.analyze via LLMService: ...
[persist] Failed to persist analysis: ...
```

The `[step]` token uses the node id from either phase (`load_job`,
`collect_sources`, `fetch_sources`, `extract_content`, `build_context`,
`validate_context`, `persist_context`, `analyze`, `extract_skills`, `score`,
`recommend`, `summarize`, `persist`). This makes it clear at a glance **which
step failed**, both in the SSE stream and in the persisted failure state.

Reasons surfaced from validation are each prefixed with the step id:

```
[validate_context] reason one
[validate_context] reason two
```

## Data tolerance

Workflow input is tolerant of missing optional data so valid jobs are not
rejected:

- **notes / links** — jobs with `notes = None` / `links = None` (or any
  non-string value) are normalized to `"[]"` when mapped into `JobData`
  (`notes_raw` / `links_raw`) rather than raising a `ValidationError`.
- **Plain-string notes / links** — a stored note or link that is a plain
  non-JSON string (the legacy worker format) is preserved as a single text
  note instead of being dropped, so a meaningful note is never silently
  ignored and reported as "empty notes".
- **Parse failures** — any error raised while building `JobData` is caught
  by `load_job`, recorded with the `[load_job]` prefix, and the execution
  is marked failed instead of crashing the worker.

## External Data Failure

Example:

- Website unavailable

Handled by:

- Node retry
- Alternative sources

---

## LLM Failure

Example:

- Provider unavailable

Handled by:

- Retry policy
- Provider fallback

---

## Workflow Failure

Example:

- Invalid state

Handled by:

- LangGraph checkpoint recovery

---

# Progress Events

Workflow nodes emit progress events.

Example:

Fetch Data Started

↓

Extract Started

↓

Analysis Started

↓

Scoring Started

↓

Persist Started

↓

Completed

Events are delivered through SSE.

Related:

docs/api/sse/processing-events.md

---

# Realized Trace-Through

How a single job URL moves through the system today, from the frontend
click to the live progress stream. Each step is a verified wiring of the
current implementation (paths + line numbers).

## 1. Frontend — user submits a job URL and starts processing

- Add-job form: `apps/frontend/src/features/jobs-v2/components/AddJobForm.tsx`
  `handleSubmit` (line 67) → `useCreateJob().createJob` →
  `POST /api/jobs` (`apps/frontend/src/features/jobs-v2/hooks/useCreateJob.ts`
  line 36).
  - **Create Job** (queue not set): creates the job record only (status
    `imported`).
  - **Create & Queue** (`queue: true`): the same `POST /api/jobs` call, but the
    backend also creates a `JOB_PROCESSING` ProcessingExecution and dispatches
    it — the job immediately follows the instant processing workflow below.
    `JobsPage.handleCreateJob`
    (`apps/frontend/src/features/jobs-v2/components/JobsPage.tsx` line 77)
    opens the Processing Queue drawer and bumps the queue reload key
    (`onJobQueued`) so the new execution shows up right away.
- Start processing (existing jobs): `apps/frontend/src/widgets/jobs-page-v2/index.tsx`
  `handleProcessV2` (line 42) calls `processMutation.mutate(id)` then opens
  the Processing Drawer. The mutation uses `jobApi.processJob`
  (`apps/frontend/src/entities/job/api.ts` line 56) → `POST /api/jobs/{jobId}/process`.
- Live progress is consumed globally by `useProcessingEvents()`
  (`apps/frontend/src/widgets/jobs-page-v2/index.tsx` line 33), hook in
  `apps/frontend/src/shared/hooks/useProcessingEvents.ts` (SSE_URL = `/events/processing`, line 8).

## 1a. API route — create + queue in one request

`apps/backend/jobs/presentation/api/jobs_v2_router.py` — `create_job`
(`POST /api/jobs`):

1. Resolves a duplicate URL (409 `JobAlreadyExistsError`).
2. Creates the job (status `imported`).
3. When `body.queue` is true, `_queue_job_for_processing(job["id"], exec_repo)`
   runs the same instant workflow as the process endpoint:
   `CreateProcessingExecutionUseCase(...).execute(...)` (creates the
   `JOB_PROCESSING` execution) then
   `DispatchProcessingExecutionService(exec_repo).dispatch(execution_id)`.
4. Returns `status: "queued"` and the `execution_id` in the response.

## 2. API route — receive the process request

`apps/backend/processing/presentation/api/process_router.py` — `process_job`
(line 21, `POST /api/jobs/{jobId}/process`):

1. Resolves the job (line 26).
2. `CreateProcessingExecutionUseCase(...).execute(...)` creates a
   `ProcessingExecution` of type `JOB_PROCESSING` (lines 33-39).
3. `DispatchProcessingExecutionService(exec_repo).dispatch(execution_id)`
   (line 41) sets status `QUEUED` and enqueues the task.

## 3. Dispatch + TaskIQ queue

- `shared/infrastructure/taskiq/client.py` — `enqueue_execution_sync` pushes
  the task id onto the broker.
- `shared/infrastructure/taskiq/config.py` — `RedisStreamBroker`.
- `shared/infrastructure/taskiq/tasks.py` — `process_execution_task`
  (line 76) runs `ProcessingExecutionRunner.run(execution_id)` via
  `asyncio.to_thread` (line 90).

## 4. Worker — ProcessingExecution runner

`apps/backend/processing/infrastructure/runner/execution_runner.py` —
`ProcessingExecutionRunner.run` (line 43):

- Marks the execution `RUNNING`, initializes `workflow_progress`, and
  publishes the `EXECUTION_STARTED` event (lines 60-70).
- Dispatches to `_run_workflow` (line 73).
- Publishes `EXECUTION_COMPLETED` / `EXECUTION_FAILED` (lines 99-105 / 82-89).

`_run_workflow` (line 123) delegates to `build_job_context_preparation_graph`
(line 144) and `graph.invoke(state)` (line 150), then — when the result is not
`FAILED` — builds and invokes the analysis graph with the same
`JobProcessingState` (lines 151-153).

## 5. Workflow — Phase 1: extraction / content prep (no LLM)

`apps/backend/processing/application/workflows/job_context_preparation/graph.py`:

- Node chain (lines 68-102): `load_job → collect_sources → fetch_sources →
  extract_content → build_context → validate_context → persist_context →
  context_ready | execution_failed`.
- Graph docstring (line 12): "This phase must NOT include any LLM calls."
- `_after_validate` routes to `persist_context` when the context is valid.

`apps/backend/processing/infrastructure/workflow/assembly.py` —
`build_job_context_preparation_graph` (line 34) wires the real infrastructure:

- `CompositeContentFetcher([HTTPXContentFetcher(), PlaywrightContentFetcher()])` (lines 39-41).
- `CompositeContentExtractor([TrafilaturaContentExtractor(), BeautifulSoupContentExtractor()])` (lines 42-44).
- `RedisProcessingEventPublisher()` (line 45).

`persist_context` writes the combined text to the job row
(`raw_description` + `description`) via `JobService.persist_prepared_context`
(`apps/backend/jobs/application/services/job_service.py` line 30), so the
analysis phase has a durable LLM input.

## 5b. Workflow — Phase 2: LLM analysis, scoring, persist

`apps/backend/processing/application/workflows/job_analysis/graph.py`:

- Node chain (lines 79-112): `load_context → prepare_profile → analyze →
  extract_skills → score → recommend → summarize → persist →
  analysis_ready | execution_failed`.
- Exactly ONE LLM call: `analyze` runs the versioned `job.analyze` prompt
  (`processing/application/services/job_analysis_prompt.py`,
  `JOB_ANALYSIS_PROMPT_VERSION` = "1.6.2", `JOB_ANALYSIS_SCHEMA_VERSION` = "1.1.0")
  via `LLMService.generate_structured(prompt, schema=…, timeout=240)`.
- Deterministic scoring (`processing/application/services/job_analysis_scoring.py`):
  scores clamped 0-100, `overall = round(fit*0.6 + success*0.4)`,
  `apply` ≥ 80 / `consider` ≥ 60 / else `skip`.
- `persist` writes three places: the `jobs` row projection, the `summaries`
  row (legacy grade via `grade_for_overall`), and the canonical `job_analysis`
  table (schema `job`) via `SQLAlchemyJobAnalysisRepository.upsert_by_job_id`.

## 5c. User-facing steps — combined workflow

`apps/backend/processing/application/workflows/workflow_step_mapper.py`
exposes a single combined workflow `WORKFLOW_ID="job_processing"`,
`WORKFLOW_NAME="Job Processing"` with 13 user-facing steps: `load_job`,
`collect_sources`, `fetch_sources`, `extract_content`, `build_context`,
`validate_context`, `persist_context`, `analyze`, `extract_skills`, `score`,
`recommend`, `summarize`, `persist`. Hidden internal nodes: `execution_failed`,
`context_ready`, `analysis_ready`, `load_context`, `prepare_profile`.

## 6. SSE progress — emit and consume

- Publishing: `apps/backend/shared/infrastructure/events/processing_events.py`
  `publish_sync` (line 123); per-entity publisher
  `apps/backend/processing/infrastructure/events/redis_processing_event_publisher.py`.
- Gateway: `apps/backend/shared/presentation/api/processing_events_router.py`
  `GET /events/processing` (line 23) → `stream_pattern(CHANNEL_PATTERN)`
  (`shared/infrastructure/events/sse.py`).
- Frontend: `useProcessingEvents.ts` opens `EventSource('/events/processing')`
  and maps events onto the react-query cache (`jobs-v2-infinite`). On
  `execution.completed` / `execution.failed` it also invalidates the
  `['job-detail', jobId]` query
  (`apps/frontend/src/shared/hooks/useProcessingEvents.ts` lines 71-89), so
  results appear live in the Job Details drawer.

## 7. Results — job detail reads the analysis block

`apps/backend/jobs/presentation/api/jobs_v2_router.py` — `GET /api/jobs/{job_id}`
(line 243) returns the job + `latest_processing_execution` + an `analysis`
block: `{ recommendation, apply_reason, scores_explanation: {fit_factors,
success_factors, concerns}, summary: {summary, resume_fit, note}, skills:
[{name, category, level, status, evidence}], insights, generated_at }`
(schemas in `apps/backend/jobs/presentation/api/schemas/jobs_v2.py`). For
legacy rows (processed before analysis existed) the block is built from the
`jobs`/`summaries` projections with no recommendation
(`_analysis_to_schema`, line 193).

The frontend Job Details drawer
(`apps/frontend/src/features/jobs-v2/components/JobDetailDrawer.tsx`) renders
an "AI Analysis" section (recommendation badge, apply reason, insights, scores
explanation, summary, tagged skills) from `JobDetail['analysis']`
(`apps/frontend/src/entities/job/types.ts` line 208) and re-fetches it via the
SSE invalidation above.

---

# Current State: Single Unified Processing Path

The trace-through above reflects the **ProcessingExecution queue** (SSE
world). The legacy Socket.IO / pending pipeline was fully retired.

Jobs AND companies both run through the shared ProcessingExecution lifecycle
(`COMPANY_PROCESSING` for companies): a two-phase workflow — context
preparation without any LLM call, then a single-LLM analysis (fetch →
extract → LLM analyze → score → persist). Live progress streams over SSE at
`/events/processing` (target_type=company for companies) and the queue is
monitored via `GET /api/processing/queue`. See
`docs/adr/020-execution-queue-vs-llm-pipeline.md` for the decision that
moved the analysis steps onto the v2 execution graph.

---

# Testing

Workflow tests should verify:

- Node behavior
- State transitions
- Failure recovery
- Provider integration
- Final result generation

---

# Related Documents

- docs/ai/workflows.md
- docs/ai/langgraph.md
- docs/ai/langgraph-state.md
- docs/domain/processing/processing-execution.md
- docs/api/processing/process-job.md
- docs/api/sse/processing-events.md
- docs/adr/020-execution-queue-vs-llm-pipeline.md
