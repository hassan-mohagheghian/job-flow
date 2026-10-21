# List Companies API

## Purpose

Returns a paginated list of Companies for the Companies page.

This endpoint is optimized for browsing, searching, filtering and sorting.

The endpoint is read-only.

Scores are exposed as **raw values from the scores blob** (they are
stored as numbers and may be fractional, e.g. `38.5`). The overall grade is `scores.overall_grade`, falling back to `fit_grade` when the former is empty.

> Company processing runs through the shared `ProcessingExecution` lifecycle
> (execution type `COMPANY_PROCESSING`), the same two-phase model as jobs: a
> context-preparation phase (no LLM) followed by a single-LLM-call analysis
> phase. Live progress is streamed over `/events/processing` with
> `target_type: "company"` and monitored via the shared Processing Drawer
> filtered to companies (no legacy pending-company polling).

---

# Endpoint

GET /api/companies/list

---

# Query Parameters

## Pagination

The list uses **cursor-based** pagination (keyset). There is no page number.

| Parameter | Type   | Required | Default |
| --------- | ------ | -------- | ------- |
| cursor    | string | No       | null    |
| page_size | integer| No       | 10      |

Maximum page_size is 100.

The first page is requested without a cursor. Each response returns the
`next_cursor` to pass for the next page.

---

## Search

| Parameter | Type   |
| --------- | ------ |
| query     | string |

Search is performed against:

- Company name
- Industry
- City
- Country
- Description

Search is case-insensitive.

---

## Filters

### Industry

```text
industry=Software Development
```

Exact match on the company's industry value.

### Company type

```text
company_type=PRODUCT_COMPANY
company_type=RECRUITING_AGENCY
company_type=STAFFING_COMPANY
```

Exact match on the company's `company_type` classification. The frontend
offers the standard values: `PRODUCT_COMPANY`, `RECRUITING_AGENCY`,
`STAFFING_COMPANY`, `CONSULTING_COMPANY`, `UNKNOWN`.

### Status

```text
status=running
status=none
```

Exact match on the company's processing status derived from its **latest**
`processing_execution` row — the same source and vocabulary the Jobs list uses
(`ExecutionStatus` values): `created`, `queued`, `starting`, `running`,
`completed`, `failed`, `cancelled`.

`status=none` matches companies that have no processing execution at all
("Not processed"). The company row's own `status` column is **not** used; it is
a partial mirror of the lifecycle and can be stale.

---

## Sorting

Supported sort fields

```text
created_at

updated_at

name

overall_score

fit_score

success_score
```

Default sort is `created_at desc` (newest first, matching the repo-wide rule).

Every sort follows a **NULLS LAST** policy: rows where the sort column is `NULL`
(for example a company that has not been scored yet) always sort **after** rows
with a value, in both `asc` and `desc` order.

Score sorts (`overall_score`, `fit_score`, `success_score`) read the
corresponding canonical key from the company's scores blob (`overall`,
`fit`, `success`) and are **multi-column** so ties on the primary score are
ordered deterministically, sharing the chosen `asc`/`desc` direction:

- `overall_score` → overall, then success, then fit
- `fit_score` → fit, then overall, then success
- `success_score` → success, then overall, then fit

Order

```text
asc

desc
```

---

# Response

```json
{
  "items": [
    {
      "id": "...",
      "name": "...",
      "industry": "...",
      "city": "...",
      "country": "...",
      "company_size": "...",
      "company_type": "...",
      "logo_url": "...",
      "website": "...",
      "description": "...",
      "job_count": 12,
      "recruiter_job_count": 0,
      "scores": {
        "overall": 88,
        "fit": 85,
        "success": 90,
        "overall_grade": "A+"
      },
      "processing": {
        "status": "completed",
        "current_node": null,
        "progress_pct": null,
        "error": null
      },
      "latest_processing_execution": {
        "id": "exec-123",
        "status": "completed",
        "started_at": "...",
        "finished_at": "..."
      },
      "parent_company_id": null,
      "main_company": null,
      "alias_count": 0,
      "is_alias": false,
      "updated_at": "...",
      "created_at": "..."
    }
  ],
  "next_cursor": "...",
  "has_more": true,
  "total_items": 128
}
```

---

# Returned Information

Each row contains only the information required by the Companies page.

Large objects must never be returned.

Excluded data includes:

- Raw/parsed HTML
- Notes
- Links
- Intelligence payloads
- Score explanation / factors / prompts
- Processing logs / history (exposed via the Processing Drawer / `/api/processing/queue`)

Those are loaded by a single detail endpoint: `GET /api/companies/list/{id}`,
which returns the company plus its notes, links, intelligence, scores and jobs
in one payload.

The only score-derived values exposed on the list are the lightweight
`scores.overall_grade` and the three `scores` values, batch-loaded per page (no
N+1). Companies without intelligence return null grades and null scores.

### Main / Alias relation

Each row includes relation fields so the list can render an `alias` badge and
relationship state without a detail call:

- `parent_company_id` — the main company's id (null when not an alias)
- `main_company` — `{ id, name }` of the main, or null
- `is_alias` — true when `parent_company_id` is set
- `alias_count` — number of companies related to this one as aliases

`latest_processing_execution` is batch-attached per page from the
`ProcessingExecution` table (no N+1); companies without an execution return
`null`.

### Jobs counts

Each row carries two derived counts, batch-computed per page from the
`job_companies` table (no N+1):

- `job_count` — number of linked, non-deleted jobs where the company is the
  hiring employer.
- `recruiter_job_count` — number of jobs the company **lists** for clients:
  recruiter-role jobs that have an attributed distinct hiring company
  (self-referencing rows and jobs without a hiring company are excluded).

The frontend shows `recruiter_job_count` for recruiter-type companies
(`RECRUITING_AGENCY` / `STAFFING_COMPANY`) and `job_count` for all others.

---

# Performance Requirements

The endpoint should support:

- Keyset pagination (indexed on the sort column + id)
- Database indexes
- Efficient filtering
- Efficient sorting

The endpoint must not perform N+1 queries. `jobs_count` is aggregated in the
same query (filtering `JobModel.deleted == 0`).

---

# Authorization

Users may only retrieve Companies they own.

---

# Errors

400

Invalid query parameters.

401

Unauthorized.

403

Forbidden.

500

Internal server error.

---

# Related Documents

- docs/ux/features/companies/page.md
- docs/ux/features/companies/company-row.md
- docs/ux/flows/companies/browse-companies.md
