# Domain Knowledge

## Core Entities

### Job
- **What**: A job posting discovered from LinkedIn, job boards, or manual submission
- **Key fields**: `num` (unique ID), `company`, `role`, `location`, `stack`, `visa`, `overall_score`, `pinned`
- **Scoring**: `fit_score` (0-100) + `success_score` (0-100) = `overall_score` (weighted 0.6/0.4)
- **States**: pending → queued → processing → done/failed
- **Pinned**: a user-managed pin flag (`pinned` integer, 0/1) to mark jobs worth pursuing; it is independent of the analysis pipeline and is toggled only through `PUT /api/jobs/{job_id}/pinned`

### JobAnalysis
- **What**: Canonical AI analysis of a single job, produced by the v2 processing pipeline's single combined `job.analyze` LLM call
- **Storage**: `job_analysis` table, one row per `job_id` (unique), upserted on every analysis
- **Key fields**: `payload` (JSON: fields, scores_explanation, summary, skills, insights), `fit_score`, `success_score`, `overall_score`, `recommendation` (apply/consider/skip), `apply_reason`, `summary`, `prompt_version`, `schema_version`, `generated_at`
- **Scoring rules**: deterministic — `overall = round(fit × 0.6 + success × 0.4)`; recommendation from overall: `apply ≥ 80`, `consider ≥ 60`, else `skip`; scores clamped to 0-100
- **Skills**: each required skill tagged `matched` / `missing` / `low` relative to the user profile, with level, category, and evidence
- **Lifecycle**: created only by the analysis phase; hard-deleted together with the job (`DELETE` on the job cascades by repository)
- **Legacy rows**: jobs processed before the analysis phase existed expose an `analysis` block built from the legacy `jobs`/`summaries` projections (no recommendation, grade-derived summary)

### Company
- **What**: A company profile with intelligence analysis
- **Key fields**: `name`, `industry`, `company_type` (Product/Recruiting), `tech_stack`, `funding_stage`
- **Intelligence**: Stored in `company_intelligence` table — overview, culture, visa, career, benefits, technology analysis + scores
- **Scores**: `company_fit_score`, `company_success_score`, `company_overall_score` (A++ to D)
- **Recruiter role**: a company may act as a recruiter/staffing agency for one or more hiring companies; the job-company associations live in `job_companies`

### JobCompany
- **What**: An association between a job and a company that the `job.analyze` extraction surfaced from the posting
- **Storage**: `job_companies` table (schema `job`), one row per (job, company, role)
- **Roles**: `hiring` (the employer, drives the job's `company_id` / display name) and `recruiter` (recruiting / staffing / consulting agency)
- **Key fields**: `job_id`, `company_id`, `role`, `company_type` (extraction vocabulary), `confidence`, `reason`
- **Lifecycle**: rows are **replaced** for the job on every re-process; hard-deleted with the job via FK cascade
- **Surfacing**: recruiters render as **Published by** in the Job detail drawer; a recruiter's hiring clients render as **Jobs listed for clients** in the Company detail drawer

### Skill
- **What**: A skill tracked in the candidate's profile
- **Categories**: Technical, Engineering, Professional, Domain, Career
- **Key fields**: `name`, `level` (1-5), `category`, `confidence`, `market_relevance`
- **Aliases**: Merged skills (e.g., Postgres → PostgreSQL) stored in `skill_aliases`

### Candidate Profile
- **What**: The canonical Candidate Profile domain (`candidates` context, schema `candidate`) — the single source of truth for all candidate intelligence. It must never depend directly on a Resume or LinkedIn; sources converge into the profile.
- **Entities**: `Candidate` (singleton person), `CandidateProfile` (aggregate root with core facts: name, title, headline, summary, location), `CandidateSource` (resume/linkedin/… each with its own independent version), `CandidateSkill` (links to `skill.skills` via logical `skill_id`, snapshot name/category, level 1-5, `confidence`, `origin` explicit/inferred, `years_of_experience`, `last_used`, `evidence`), `CandidateExperience`, `CandidateProject`, `CandidateEducation`, `CandidateCertificate`, `CandidateInterest`, `CandidateLanguage`, `CandidateProfileVersion` (immutable snapshot per merge).
- **Provenance (Evidence)**: every extracted entity carries `sources` (e.g. `["resume","linkedin"]`) + `confidence` (0-1) + notes; explicit vs inferred skills are distinguished.
- **Versioning**: each merge produces a new `CandidateProfileVersion`; sources version independently (updating Resume must not reprocess LinkedIn).
- **Persistence**: within-context FKs only; the cross-context `skill_id` link to `skill.skills` is a logical reference (no FK, AGENTS.md rule 15).
- **Extraction**: `CandidateExtractService` (one `candidate.extract` LLM call per source via `LLMService.generate_structured`, versioned prompt/schema + strict validation) turns a raw source document into the structured profile. Source adapters (`CandidateSourceAdapter` → `ResumeAdapter` / `LinkedInAdapter`) read the latest `candidate.candidate_sources` row for their `source_type` (GitHub/Portfolio are stubs). Extracted skills resolve into `skill.skills` via `resolve_skill`; skills mentioned in a document are stored `origin=explicit` with `Evidence` and confidence; the `inferred` origin is reserved for merge/inference phases.
- **Merge (ProfileMergeService)**: the single persistence primitive — folds every extracted payload into the canonical profile deterministically and idempotently. Core fields (name/title/headline/summary/location): incoming non-empty wins. Natural keys: skills by `skill_id` (fallback name; keep max level/confidence/years, union evidence sources), experiences by `(company, role)`, projects by `name`, educations by `(institution, degree)`, certificates by `name`, interests/languages by `name`. Removed = present in current but absent from incoming. Every merge writes core + all child sets + a new `CandidateProfileVersion` snapshot (`v1` for the first merge, then `version+1`) with a `source_versions` map and a `change_summary` derived from the diff.
- **Events (EDD)**: domain events (see `docs/domain/candidates/events.md`) are emitted through the `CandidateEventPublisher` port during merge/extract operations. The default implementation is an in-memory collector — pub/sub transport is deferred (AGENTS.md rule 16).

### CandidateSource
- **What**: A resume or LinkedIn profile uploaded as analysis input — never generated
- **Storage**: `candidate.candidate_sources` table; `source_type` is `resume` or `linkedin`
- **Upload**: via `POST /api/candidates/sources` (body `{source_type, raw_text}`), stored with `version` auto-incremented per source type
- **PII**: `raw_text` is PII-masked (name line, phone, email, LinkedIn/GitHub URLs) at save time
- **Status**: `pending` on upload, `processed` after the next candidate processing run extracts it
- **Latest**: the row with the highest `version` for the `source_type`

### Application
- **What**: A per-job application record (`applications` context, schema `application`) that drives the Job Application Workspace (`/jobs/{job_id}/application`). Aggregates follow-ups and versioned documents (tailored resume / cover letter).
- **Cross-context**: `job_id` is a logical reference to the Jobs context — plain column, no FK (AGENTS.md rule 15). At most one application per job; creation defaults status to `recommended`.
- **Status**: `seen` → `preparing` → `ready_to_apply` → `applied` (outcomes `rejected` / `withdrawn` / `expired`).
- **Artifacts**: `application_documents` (markdown content, `document_type` `tailored_resume` | `cover_letter`), versioned per successful generation. A skill-gap roadmap for the application lives in the Roadmaps context (source `APPLICATION`).
- **Generation**: documents are produced asynchronously by the processing pipeline (`application_resume` / `application_cover_letter` executions) — a consumer of existing job/company/candidate intelligence, never a re-analysis.
- **Events (EDD)**: domain events (see `docs/domain/applications/events.md`) are emitted through the `ApplicationEventPublisher` port during create/update/follow-up/document operations; the default implementation is an in-memory collector — pub/sub transport is deferred (AGENTS.md rule 16).

### Roadmap
- **What**: A user goal broken into milestones and tasks (`roadmaps` context, schema `roadmap`), with optional skill links, notes and learning resources. Independent from Applications: an application is only a logical reference (`application_id`, no FK).
- **Cross-context**: `roadmaps.application_id` and `roadmap_skill_links.skill_id` are logical references (AGENTS.md rule 15); skills attach via `SQLAlchemySkillRepository.resolve_skill`.
- **Sources / status**: `MANUAL` (default) / `APPLICATION` / `AI_GENERATED`; roadmap status `ACTIVE` / `COMPLETED` / `ARCHIVED`. Tasks and milestones carry `NOT_STARTED` / `IN_PROGRESS` / `COMPLETED` (+ `SKIPPED` for tasks).
- **Progress**: computed, not stored — `completed (or skipped) tasks / total tasks`, per milestone and overall (0 when no tasks).
- **Events (EDD)**: domain events (see `docs/domain/roadmaps/events.md`) are emitted through the `RoadmapEventPublisher` port during create/update/delete/milestone/task/note/resource/skill-link operations; the default implementation is an in-memory collector — pub/sub transport is deferred (AGENTS.md rule 16).

## Business Rules

### Scoring System
- **SHARED rules**: Apply to all entities (visa probability, communication fit)
- **JOB rules**: Job-specific scoring (fit_score, success_score)
- **COMPANY_PRODUCT rules**: Product company scoring
- **COMPANY_RECRUITING rules**: Recruiting agency scoring
- **Formula**: `overall_score = fit_score × 0.6 + success_score × 0.4`

### Scoring Rules
- Each rule has a single `priority` (0–100) that drives **list order**
  (descending), the **severity badge** (≥90 Critical, ≥75 High, ≥50 Med, else
  Low) and the **LLM weight** (`w:{priority}`) injected into scoring prompts.
- Rules are scoped: `SHARED`, `JOB`, `COMPANY_PRODUCT`, `COMPANY_RECRUITING`.
- Reordering writes `priority = neighbor ± 1` (move up/down, clamped 0–100) or
  redistributes the column on drag-and-drop.

### Visa Assessment
- **BEST**: Confirmed sponsorship, English-first, international team
- **Strong**: Likely sponsorship, international presence
- **Good**: Possible sponsorship, English environment
- **Moderate**: Unclear, may require local authorization
- **Uncertain**: No visa signals found

### Processing Pipeline
1. **Fetch**: Download URL content (supports notes+links for multi-source)
2. **Validate**: Verify it's a real job posting
3. **Extract**: Parse structured fields (title, company, role, stack, etc.)
4. **Score**: Apply scoring rules, calculate fit/success/overall
5. **Save**: Write to DB with deduplication check

### Job Processing Pipeline (v2, SSE)
Runs as a single `ProcessingExecution` (`JOB_PROCESSING`) driven by the runner
over two LangGraph phases:

**Phase 1 — Context Preparation (no LLM)**
1. `load_job` → `collect_sources` → `fetch_sources` → `extract_content` → `build_context` → `validate_context`
2. `persist_context`: writes the combined text to the job row (`raw_description` + `description`) so the analysis phase has a durable LLM input
3. `context_ready` / `execution_failed`

**Phase 2 — Job Analysis (one LLM call)**
1. `load_context` (read prepared content) → `prepare_profile` (skills, latest resume + LinkedIn, scoring rules)
2. `analyze`: single `job.analyze` call via `LLMService.generate_structured` (only provider entry point); the prompt carries the latest resume and LinkedIn as labeled profile-documents sections — the resume is authoritative for skills/seniority, LinkedIn supplements it
3. `extract_skills` (normalize + tag matched/missing/low) → `score` (deterministic overall/recommendation) → `recommend` → `summarize`
4. `persist`: update the jobs row projection + summaries row (legacy grade) + `job_analysis` row
5. `analysis_ready` / `execution_failed`

Each step emits SSE `workflow.step.*` events; the frontend refetches the Job
Details on `execution.completed|failed`.

### Candidate Processing Pipeline (v2, SSE)
Runs as a single `ProcessingExecution` (`CANDIDATE_PROCESSING`, target
`candidate` / `profile_id`) driven by the runner over two LangGraph phases:

**Phase 1 — Source Preparation (no LLM)**
1. `load_profile`: load (or create) the canonical candidate profile
2. `prepare_sources`: collect raw content for every available source via the
   adapters (resume/linkedin/github/portfolio), skipping already-known versions
3. `sources_ready` / `execution_failed`

**Phase 2 — Extraction + Merge (one `candidate.extract` LLM call per new source)**
1. `extract`: run `candidate.extract` per pending source (validate + retry once);
   per the approved decision an extraction failure fails the whole run
2. `merge`: `ProfileMergeService` folds all extracted payloads into the profile,
   writes core + children + a `CandidateProfileVersion` snapshot and marks the
   sources processed
3. `candidate_ready` / `execution_failed`

Each step emits SSE `workflow.step.*` events; the candidate domain events
(`candidate.*`) are collected in-memory by the `CandidateEventPublisher` port.

### Candidate Source Upload Pipeline

Resume and cover letter **generation was removed** from the platform. Resumes and
LinkedIn profiles exist only as **candidate sources** (`candidate.candidate_sources`)
uploaded through `POST /api/candidates/sources` and used as labeled context in job
analysis. Upload → PII-mask → `pending`; the candidate processing pipeline
extracts them into the canonical profile and marks them `processed`.

## Domain Workflows

### Job Application Flow
```
URL submitted → queued → fetching → validating → extracting → scoring → saved
```

### Company Research Flow
```
Notes/Links added → queued → fetching → extracting → analyzing → saved
```

### Career Intelligence Flow
```
Generate All → overview → opportunities → companies → market → networking → skills_intel
```

### Candidate Source Upload Flow
```
Resume/LinkedIn uploaded → PII-masked → pending → candidate processing extract → processed
```

### Application Generation Flow
```
Generate clicked → ProcessingExecution (roadmap_generation / application_resume / application_cover_letter)
  → queued → runner builds the graph state (roadmap or application intelligence)
  → load_context (job + job_skills + company + candidate) → generate (LLMService) → persist
  → roadmap row / document row (versioned) → SSE progress → workspace refetches
```

### Job Application Flow
```
Create application (recommended) → prepare (plan + documents) → applied (timeline records the date) → follow-ups
```
