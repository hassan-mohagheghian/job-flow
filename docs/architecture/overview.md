# Architecture Overview

Job Search Intelligence is a **DDD modular monolith** with a hexagonal backend (FastAPI) and a Feature-Sliced frontend (Next.js).

---

## System Diagram

```
┌──────────────────────────────────────────────┐
│              Next.js (App Router)            │
│  ┌────────┐ ┌──────────┐ ┌───────────────┐  │
│  │  Jobs  │ │Companies │ │Skills/CandProfile │  │
│  └───┬────┘ └────┬─────┘ └───────┬───────┘  │
│      │           │               │          │
│  FSD: entities / features / widgets / shared │
└──────┼───────────┼───────────────┼──────────┘
       │           │               │
       │       HTTP REST + SSE     │
┌──────┼───────────┼───────────────┼──────────┐
│      ▼           ▼               ▼          │
│        FastAPI (port 5000)                  │
│  ┌───────────────────────────────────────┐  │
 │  │ Bounded Contexts                      │  │
 │  │ jobs · companies · skills · rules     │  │
 │  │ candidates · ai · processing · shared │  │
 │  │ applications · roadmaps · opportunities │  │
│  └───────┬───────────────────────┬───────┘  │
│          │                       │          │
│   ┌──────▼──────┐         ┌──────▼──────┐   │
│   │ PostgreSQL   │         │   Redis     │   │
│   │ (SQLAlchemy) │         │  (broker)   │   │
│   └──────────────┘         └──────┬──────┘   │
└───────────────────────────────────┼─────────┘
                                    │
                     ┌──────────────▼──────────────┐
                     │        TaskIQ Worker        │
                     │        (background)         │
                     └──────────────┬──────────────┘
                                    │
                     ┌──────────────▼──────────────┐
                     │       LLMService (AI)       │
                     │      LangGraph workflows    │
                     │  ┌──────┬──────┬────────┐   │
                     │  │OpenAI│ Mimo │ Local  │   │
                     │  └──────┴──────┴────────┘   │
                     └─────────────────────────────┘
```

---

## Architecture Layers

| Layer          | Responsibility                                    |
| -------------- | ------------------------------------------------- |
| Presentation   | FastAPI routers, Pydantic schemas, SSE endpoints  |
| Application    | Use cases, services, commands, DTOs               |
| Domain         | Entities, value objects, repository interfaces, events |
| Infrastructure | SQLAlchemy models/repositories, workers, AI providers, prompts |
| Shared Kernel  | Config, logging (structlog), DI, database          |

---

## Bounded Contexts

| Context    | Purpose                                                        |
| ---------- | -------------------------------------------------------------- |
| jobs       | Job lifecycle: import, process, score, list                    |
| companies  | Company profiles, intelligence, visa assessment                |
| skills     | 5-category taxonomy, aliases, relationships, insights           |
| candidates | Canonical Candidate Profile domain: profile, sources, skills/experience/projects, evidence, versions; source adapters (resume/linkedin) + one `candidate.extract` LLM call |
| applications | Job Application Workspace: per-job application record, follow-ups, versioned documents (tailored resume / cover letter); generation via the processing pipeline |
| opportunities | Inbound Opportunity pipeline: manual message → extract → resolve existing job/company → evaluate vs candidate profile + rules → score → application path → funnel tracking |
| roadmaps    | Independent user goal broken into milestones/tasks with skill links; AI generation from an application via the processing pipeline |
| rules      | Configurable scoring rules (SHARED, JOB, COMPANY_PRODUCT, ...) |
| ai         | LLMService, providers, tools, LangGraph graphs                     |
| processing | ProcessingExecution, workflow progress, events, queue, job analysis graphs |
| shared     | Shared Kernel used by all contexts                              |

Contexts must not cross-import. Dependencies flow domain → application → infrastructure → presentation.

---

## AI Layer

- **LLMService** — single facade for all AI calls; providers are never called directly.
- **Provider abstraction** — swap via `AI_PROVIDER` env var (openai, mimo, local, gemini, ...).
- **LangGraph workflows** — stateful pipelines: `JobContextPreparationGraph` (LLM-free prep) → `JobAnalysisGraph` (single combined `job.analyze` call), the company two-phase workflow (`COMPANY_PROCESSING` `ProcessingExecution`: context preparation without LLM, then a single-LLM analysis), the candidate two-phase workflow (`CANDIDATE_PROCESSING` `ProcessingExecution`: `CandidateSourcePreparationGraph` collects source contents (no LLM) → `CandidateProcessingGraph` runs one `candidate.extract` call per new source and merges everything into the canonical profile with a `CandidateProfileVersion` snapshot), and the application generation workflows (`RoadmapGenerationGraph` — `roadmap_generation`, and `ApplicationIntelligenceGraph` — `application_resume` / `application_cover_letter` `ProcessingExecution`s: load context → generate → persist, reusing the job analysis / company / candidate context builders without re-analysis).
- **Candidate events (EDD)** — the Candidates context emits domain events (`candidate.*`) through the `CandidateEventPublisher` port; the default implementation is an in-memory collector (`InMemoryEventCollector`). Pub/sub / SSE / outbox transport is deferred to a dedicated phase (AGENTS.md rule 16). Catalog: `docs/domain/candidates/events.md`.
- **Job Analysis prompt** — the `job.analyze` prompt and its output JSON schema are versioned and self-contained in `processing/application/services/job_analysis_prompt.py`; called via `LLMService.generate_structured`. The obsolete `ai/infrastructure/prompts/` package and unused `jobs/infrastructure/ai/prompts/*.py`/`.md` prompt modules were removed.

---

## Background Execution

```
API → ProcessingExecution → TaskIQ task → TaskIQ worker → LangGraph workflow → result + events
```

- TaskIQ owns background execution and retries.
- LangGraph owns workflow state and node execution.
- The `ProcessingExecutionRunner` runs both graphs for `JOB_PROCESSING` (and `COMPANY_PROCESSING` / `CANDIDATE_PROCESSING` / the `APPLICATION_*` types): context preparation first, then the analysis/merge graph reusing the same state.
- Progress is exposed to the frontend through SSE events.

---

## Realtime (SSE)

- `GET /api/sse/processing-events` streams user-facing execution events.
- Frontend combines a REST snapshot (`/api/processing/queue`) with the SSE stream for live UI.
- On `execution.completed` / `execution.failed` the frontend refetches the Job Details so the analysis block appears without a reload.

---

## Data Flow — Job Processing

```
Job URL
  ↓
ProcessingExecution (created)
  ↓
TaskIQ background task
  ↓
Phase 1 (no LLM): load job → collect sources → fetch → extract → build context → validate → persist context
  ↓
Phase 2 (one LLM call): load context → prepare profile → analyze (job.analyze) → extract skills → score → recommend → summarize → persist
  ↓
SSE progress events
  ↓
Save result: jobs projection + summaries + job_analysis
```

---

## Design Decisions

- DDD modular monolith + hexagonal architecture (8 contexts)
- SQLAlchemy ORM + Alembic (never raw SQL)
- FastAPI + Pydantic v2 (automatic OpenAPI docs)
- Feature-Sliced frontend (entities / features / widgets / shared)
- Provider abstraction for all AI calls
- LangGraph for multi-step AI pipelines
- TaskIQ + Redis for background processing
- SSE for real-time processing visualization

---

## More Details

- `docs/architecture/ARCHITECTURE.md` — full system design
- `docs/architecture/` — bounded-context analysis, DDD structure, dependency rules
- `docs/ai/` — AI architecture, LangGraph, prompt platform
- `docs/domain/` — domain entities and processing execution (incl. `docs/domain/applications/`)
- `docs/queue/` — TaskIQ / ARQ processing
