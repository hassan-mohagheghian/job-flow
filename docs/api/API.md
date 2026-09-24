# API Overview

REST API served by FastAPI on port 5000. All endpoints return JSON. Real-time processing updates are delivered through Server-Sent Events (SSE).

**Base URL**: `http://localhost:5000`

**Interactive docs**: Swagger UI `/api/docs/`, ReDoc `/api/redoc/`, OpenAPI spec `/api/openapi.json`

---

## Quick Reference

| Group               | Base Path                                   | Purpose                               |
| ------------------- | ------------------------------------------- | ------------------------------------- |
| Jobs                | `/api/jobs`                                 | List, create, update, delete, pin jobs |
| Processing          | `/api/jobs/{job_id}/process`                | Start a Processing Execution          |
| Processing Queue    | `/api/processing/queue`                     | Snapshot of active executions         |
| Execution Detail    | `/api/processing/executions/{execution_id}` | Execution status + workflow progress  |
| Execution Actions   | `/api/processing/executions/{id}/...`       | Start, cancel, retry, remove queue entry |
| Companies           | `/api/companies`                            | Company intelligence CRUD             |
| Cities              | `/api/cities`                               | Normalized city catalog (read-only)   |
| Skills              | `/api/skills`                               | Skill CRUD, aliases, merge, breakdown, jobs referencing a skill |
| Insights            | `/api/insights`                             | Career intelligence sections          |
| Candidate Profile   | `/api/candidates/sources`                   | Resume / LinkedIn profile upload as analysis input |
| Applications        | `/api/applications`                        | Job application workspace: follow-ups, documents, generation |
| Rules               | `/api/rules`                                | Scoring rules configuration           |
| SSE                | `/api/sse/processing-events`                | Real-time processing event stream     |
| System              | `/api/generation-history`, `/api/health`    | History + health check                |

---

## Authentication

None. All endpoints are publicly accessible.

## Errors

All errors return JSON with the appropriate HTTP status (400, 404, 409, 500):

```json
{ "error": "<message>" }
```

## Versioning

No explicit API versioning. Breaking changes are avoided by maintaining backward compatibility.

---

## Job Details + Analysis

`GET /api/jobs/{job_id}` returns the full job record plus the `analysis`
block produced by the Job Analysis phase:

```json
{
  "id": "…",
  "title": "Senior Backend Engineer",
  "company_name": "Acme Inc",
  "rank": 3,
  "pinned": true,
  "scores": { "overall": 79, "fit": 85, "success": 70 },
  "analysis": {
    "recommendation": "consider",
    "apply_reason": "Great role overall.",
    "scores_explanation": {
      "fit_factors": ["Python backend experience"],
      "success_factors": ["Senior level"],
      "concerns": ["No Kafka experience"]
    },
    "summary": { "summary": "…", "resume_fit": "…", "note": "…" },
    "skills": [{ "name": "Python", "category": "Language", "level": 4, "status": "matched", "evidence": "…" }],
    "insights": ["…"],
    "generated_at": "2026-08-03T12:00:00+00:00"
  },
  "latest_processing_execution": { "…": "…" },
  "related_companies": [
    { "company_id": "…", "name": "RecruitCo", "role": "recruiter", "company_type": "recruiting_agency", "confidence": 0.9, "reason": "listed as recruiting partner" }
  ],
  "description": "…"
}
```

- `analysis` is `null` until the analysis phase completes for the job.
- `rank` is the job's competition rank (`RANK()`) in the full job list sorted by
  **overall, then success, then fit** score (each descending, NULLS LAST); jobs
  with identical scores share a rank and the next distinct rank skips ahead.
  Jobs without a score sort last (after all scored jobs). It is derived at read
  time, never stored, and uses the same window as the list, so the detail rank
  always matches the list rank.
- For jobs processed before the analysis phase existed, `analysis` is a
  backward-compatible block built from the legacy `jobs`/`summaries`
  projections (no `recommendation`, grade-derived `summary`).
- `related_companies` lists every company associated with the job via the
  `job_companies` table: the `hiring` company (the employer that drives
  `company_id`) plus any `recruiter` / staffing / agency companies extracted
  from the posting. The frontend renders the recruiters under **Published by**
  in the Job Details drawer.
- The frontend refetches this endpoint on `execution.completed` /
  `execution.failed` SSE events so results appear live in the Job Details drawer.

---

## Company Type

`companies.company_type` is always one of the **fixed vocabulary**
(`PRODUCT_COMPANY`, `RECRUITING_AGENCY`, `STAFFING_COMPANY`,
`CONSULTING_COMPANY`, `UNKNOWN`). Both `PUT /api/companies/{id}` (manual edit)
and processing `persist_analysis` normalize through
`normalize_company_type`: an empty value clears the field (`null`), a
recognized value is uppercased, and anything else is stored as `UNKNOWN`. A
company reprocess (`POST /api/companies/{id}/reprocess`) with more links/notes
re-detects and corrects an inaccurate type. See
`docs/domain/companies/company_type.md`.

---

## Pinned

Each job carries a user-managed `pinned` flag (`true`/`false`). It is managed
exclusively through its own endpoint and is **not** part of the edit-job
payload.

### `GET /api/jobs/list?pinned=true`

Restricts the jobs list to pinned jobs. Omitted (or `false`) returns all
jobs. Each list item exposes the `pinned` flag plus a lightweight
`recommendation` field (`apply` / `consider` / `skip`, `null` without a
completed analysis) — the full analysis block stays on the detail endpoint.

The list also supports `recommendation=apply|consider|skip` to filter to jobs
whose analysis produced that recommendation (jobs without analysis never
match), and `created_date=today|yesterday|week|month` to filter by the job's
creation date preset.

### `GET /api/jobs/timeline`

Returns the number of non-deleted jobs created per calendar day, newest first,
grouped by the day portion of `created_at`. Display-only; independent of list
filters.

```json
{
  "days": [ { "date": "2026-08-19", "count": 3 }, { "date": "2026-08-18", "count": 5 } ],
  "total": 8
}
```

`total` is the sum of all day counts. The frontend renders this in the narrow
"Jobs added" side panel on the Jobs page.

### `PUT /api/jobs/{job_id}/pinned`

Request: `{ "pinned": true }` → Response `200`: `{ "pinned": true }`, or
`404` when the job is unknown.

---

## Candidate Profile Sources (Resume + LinkedIn)

The latest resume and the latest LinkedIn profile are stored as **candidate
sources** (`POST /api/candidates/sources`) and fed into job analysis as
labeled extra context. The resume is authoritative for skills and seniority;
LinkedIn supplements it. "Latest" is the highest `version` for that
`source_type`.

### `GET /api/candidates/sources` — list sources

Returns all candidate sources, newest version first.

### `POST /api/candidates/sources` — upload a resume or LinkedIn profile

Request: `{ "source_type": "resume" | "linkedin", "raw_text": "…" }`.
Response `201`: `{ "id": "…", "source_type": "…", "version": 1, "status": "pending" }`.

PII (name line, phone, email, LinkedIn/GitHub URLs) is masked before saving;
the source is left `pending` until the next candidate processing run extracts
and marks it `processed`.

### `GET /api/candidates/versions` — list profile versions

### `POST /api/candidates/analyze` — run candidate processing

---

## Full Reference

For endpoint-by-endpoint documentation see `docs/api/api-design.md` (conventions) and the per-context docs under `docs/api/`.
- `docs/api/` — per-domain API specs (`jobs/`, `processing/`, `companies/`, `cities/`, `applications/`, `sse/`, ...)

## Applications (Job Application Workspace)

The Applications API (`/api/applications`) backs the Job Application Workspace.
It tracks a per-job application (status, status timeline, follow-ups) and queues
AI generation of a tailored resume, cover letter and a job-preparation roadmap
through the processing pipeline (see `docs/api/applications/README.md`,
`docs/ai/application-intelligence.md` and `docs/ai/roadmap-generation.md`).

Endpoints:

- `GET /api/applications/by-job/{job_id}` — application detail for a job.
- `POST /api/applications` — create an application (`{ "job_id" }`, default status `recommended`).
- `PATCH /api/applications/{application_id}` — update `status` / `applied_at` (status change records a timeline node).
- `PATCH` / `DELETE` `/api/applications/timeline/{timeline_id}` — edit `changed_at` / remove a status-timeline node.
- `POST /api/applications/{application_id}/follow-ups` — add a follow-up.
- `PATCH` / `DELETE` `/api/applications/follow-ups/{follow_up_id}` — update / delete a follow-up.
- `POST /api/applications/{application_id}/roadmap/generate` — queue roadmap generation (202).
- `POST /api/applications/{application_id}/documents/{type}/generate` — queue resume / cover letter (202).
- `PATCH` / `DELETE` `/api/applications/documents/{document_id}` — edit / delete a document.
- `GET /api/applications/documents/{document_id}/pdf` — download a document as a PDF (placeholders filled).

## Placeholders API (`/api/placeholders`)

User-supplied personal details injected into generated documents (`{{token}}`).

- `GET /api/placeholders` — list canonical keys (with labels) + saved values.
- `PUT /api/placeholders` — upsert a flat `{key: value}` map.

See `docs/api/placeholders/README.md`.
