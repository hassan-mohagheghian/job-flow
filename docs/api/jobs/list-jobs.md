# List Jobs API

## Purpose

Returns a paginated list of Jobs for the Jobs page.

This endpoint is optimized for browsing, searching, filtering and sorting.

The endpoint is read-only.

Each row carries a small projection of the job's **latest processing execution**
(id, status, started/finished timestamps). Live, step-by-step progress is
retrieved separately through SSE.

A job that has never been processed has `latest_processing_execution` set to
`null` and `job_status` set to `null`. Processing status comes exclusively from
`processing_executions` — the legacy `jobs.status` column is not used by this
endpoint.

---

# Endpoint

GET /api/jobs

---

# Query Parameters

## Pagination

| Parameter | Type    | Required | Default |
| --------- | ------- | -------- | ------- |
| page      | integer | No       | 1       |
| page_size | integer | No       | 25      |

Maximum page_size is 100.

---

## Search

| Parameter | Type   |
| --------- | ------ |
| query     | string |

Search is performed against:

- Job title
- Company name
- Location
- Raw keywords
- Job posting URL

Pasting a job link (or any unique URL fragment) into `query` matches the job's
`url` value case-insensitively, so a job can be located by its link.

Search should be case-insensitive.

---

## Filters

### Processing Status

```text
processing_status=

queued
starting
running
completed
failed
cancelled
none
```

A job matches only when its **latest** execution (by `created_at`) has the given
status. Jobs with no execution are never returned by this filter, regardless of
the legacy `jobs.status` value.

The special value `none` returns the inverse: only jobs that have **no**
processing execution at all (never queued). It is exclusive with the other
values.

The `processing_status` filter is the only status filter. The legacy
`jobs.status` values (`imported`, `processed`, `archived`) are not part of the
list model and cannot be filtered on here.

---

### Company

```text
company_id
```

---

### Location

```text
location=Berlin
```

Case-insensitive substring match against the job's `location` value. A job
matches when its location contains the given text anywhere in the string (e.g.
`location=berlin` matches `Berlin, Germany`). Empty value is ignored.

---

### Remote

```text
remote=true
```

---

### Visa

```text
visa=true
```

---

### Pinned

```text
pinned=true
```

Filters to jobs the user has pinned. Omitted (or `false`) returns all jobs.

---

### Recommendation

```text
recommendation=apply
```

Filters to jobs whose analysis produced the given recommendation (`apply`,
`consider`, or `skip`). Jobs without a completed analysis never match. Omitted
returns all jobs.

---

### Tracking Status

```text
tracking_status=applied
```

Filters to jobs by their **application funnel** status, derived from the
application record (logical `job_id` reference — the value is not stored on the
job). Values:

- `not_applied` — the job has no application record.
- `seen`, `preparing`, `ready_to_apply`, `applied`, `interview`,
  `offer`, `accepted`, `rejected`, `withdrawn`, `expired` — match jobs whose application
  status equals the value.

`not_applied` returns jobs with **no** application; any other value returns only
jobs whose application status matches. Omitted returns all jobs. Combinable with
`processing_status`.

---

### Created Date

```text
created_date=today
```

Filters to jobs by their `created_at` date, using one of four presets:

- `today` — created on the current day (from 00:00:00 UTC).
- `yesterday` — created on the previous calendar day.
- `week` — created within the last 7 days.
- `month` — created within the last 30 days.

Omitted returns all jobs. Combinable with the other filters. `created_at` is a
Text column, so it is cast to a timestamp and compared against naive UTC
boundaries (handles both the space-separated fresh-insert layout and the ISO `T`
layout).

---

### Score Range

```text
overall_score_min

overall_score_max
```

---

## Sorting

Supported sort fields

```text
updated_at

created_at

overall_score

fit_score

success_score

company

title

status
```

The `status` sort orders rows by the same execution status each row displays —
the **latest** execution's status — so the sort never disagrees with the row.
Statuses are grouped alphabetically and a job that has never been processed
(no execution) always sorts **last**, in both `asc` and `desc` order. Cursor
pagination for `status` uses a composite cursor (`<rank>:<job_id>`) so pages
stay consistent and never skip or duplicate rows.

Every sort follows a **NULLS LAST** policy: rows where the sort column is
`NULL` (for example a job that has not been scored yet) always sort **after**
rows with a value, in both `asc` and `desc` order. The policy applies to every
sortable column, not just `status`.

Score sorts (`overall_score`, `fit_score`, `success_score`) are **multi-column**
so that rows tied on the primary score are ordered deterministically, sharing
the chosen `asc`/`desc` direction:

- `overall_score` → overall, then success, then fit
- `fit_score` → fit, then overall, then success
- `success_score` → success, then overall, then fit

For multi-column score sorts the keyset cursor is `v1|v2|v3|job_id` (one value
per tiebreak column plus the id), still NULLS LAST on every column.

All other sorts behave as before, except that the keyset cursor is now a
composite `<value>|<job_id>` (the `status` cursor is `<rank>:<job_id>`). The
composite form is required so that cursor pagination can walk the NULL tail
(NULL rows sort last and are reached only after every valued row) without
skipping or duplicating rows. A legacy single-value cursor (no `|`) is still
accepted for a transition period.

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
      "title": "...",
      "company_name": "...",
      "location": "...",
      "remote": true,
      "visa_sponsorship": false,

      "job_status": "completed",

      "pinned": false,

      "recommendation": "apply",

      "tracking_status": "applied",

      "rank": 7,

      "latest_processing_execution": {
        "id": "...",
        "status": "completed",
        "started_at": "...",
        "finished_at": "..."
      },

      "scores": {
        "overall": 91,
        "fit": 94,
        "success": 88
      },

      "updated_at": "...",
      "created_at": "..."
    }
  ],

  "pagination": {
    "page": 1,
    "page_size": 25,
    "total_items": 523,
    "total_pages": 21
  }
}
```

---

# Returned Information

Each row should contain only the information required by the Jobs page.

Large objects must never be returned.

Excluded data includes:

- Raw HTML
- Parsed HTML
- Prompt history
- Full analysis block (`apply_reason`, `scores_explanation`, `skills`, ...)
- Processing logs
- Timeline
- LLM output

Those are loaded by dedicated endpoints.

The `rank` field on each list item is the job's position in the full non-deleted
job list sorted by overall, then success, then fit score (each descending,
NULLS LAST). It uses **competition ranking** (`RANK()`): jobs with identical
scores share a rank and the next distinct rank skips ahead. It is absolute —
independent of the list's current `sort`/`order`/filters. It is computed for the
whole page in a single PostgreSQL `RANK()` window query (one query per request,
no N+1); unscored jobs always rank last (NULLS LAST).

The only analysis-derived value exposed on the list is the lightweight
`recommendation` field (`apply` / `consider` / `skip`), batch-loaded per page
(no N+1). Jobs without a completed analysis return `recommendation = null`.

The lightweight `tracking_status` field exposes the job's application funnel
status (`not_applied` or an application status), batch-loaded per page via the
application repository (logical `job_id` reference, AGENTS.md rule 15). Jobs
without an application return `not_applied`. It is **not** stored on the job.

The job detail endpoint (`GET /api/jobs/{job_id}`) is the one that returns the
full analysis block, not this list:

```json
{
  "analysis": {
    "recommendation": "apply",
    "apply_reason": "...",
    "scores_explanation": {
      "fit_factors": ["..."],
      "success_factors": ["..."],
      "concerns": ["..."]
    },
    "summary": {
      "summary": "...",
      "resume_fit": "...",
      "note": "..."
    },
    "skills": [
      { "name": "Python", "category": "Language", "level": 4, "status": "matched", "evidence": "..." }
    ],
    "insights": ["..."],
    "generated_at": "..."
  }
}
```

For jobs processed before the analysis phase existed, the block is built from
the legacy `jobs`/`summaries` projections (no recommendation).

---

# Pin Job

Toggles the user's pinned flag on a job. This is the **only** way the flag is
managed — it is not part of the edit-job payload.

## Endpoint

PUT /api/jobs/{job_id}/pinned

## Request Body

```json
{
  "pinned": true
}
```

## Response

200

```json
{
  "pinned": true
}
```

404

Job not found.

---

# Set Job Company

Links a job to a company, or unlinks it. This is the **only** way the
`company_id` relation is managed — it is not part of the edit-job payload.

## Endpoint

PUT /api/jobs/{job_id}/company

## Request Body

```json
{
  "company_id": "019fd657-7769-776c-be0d-9e3b843452cb"
}
```

`company_id` may be `null` (or an empty string) to unlink the job. Linking also
sets the job's stored company name to the company's canonical name; unlinking
leaves the stored name untouched.

## Response

200 — updated job detail payload (see `GET /api/jobs/{job_id}`), with the new
`company_id` / `company_name` reflected.

404

Job not found, or the given `company_id` does not reference an existing company.

---

# Performance Requirements

The endpoint should support:

- Pagination
- Database indexes
- Efficient filtering
- Efficient sorting

The endpoint must not perform N+1 queries.

---

# Authorization

Users may only retrieve Jobs they own.

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

- docs/domain/jobs/job-search.md
- docs/ux/features/jobs/page.md
- docs/api/processing/process-job.md
