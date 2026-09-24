# Company Detail API

## Purpose

Returns a single Company with **all** related information in one payload:

- Base profile fields (name, industry, location, size, website, description, ...)
- Processing status (`status`, `current_node`, `progress_pct`, `error`)
- Original notes
- Company links
- Intelligence analysis (`overview`, `culture_analysis`, ...)
- Scores (`fit`, `success`, `overall`, `overall_grade`)
- Linked jobs (slim projection)
- `job_count`

This mirrors the Jobs v2 detail pattern: the drawer fetches once and every tab
reads from the same payload. No separate `/links`, `/jobs` or local-history
calls are needed for the Company detail drawer.

> Company processing runs through the shared `ProcessingExecution` lifecycle
> (execution type `COMPANY_PROCESSING`), the same two-phase model as jobs:
> context preparation without LLM, then a single-LLM analysis call. `status` is
> derived from the company's **latest** execution, using the shared execution
> vocabulary (`created` → `queued` → `starting`/`running` → `completed` /
> `failed` / `cancelled`). Live progress is exposed via `/api/processing/queue`
> and SSE events (`/events/processing`, `target_type: "company"`), and is
> monitored through the shared Processing Drawer filtered to companies.

---

# Endpoint

GET /api/companies/list/{id}

The route is registered on the companies v2 router, which is mounted **before**
the legacy companies router, so it shadows the legacy `GET /api/companies/{id}`
for the same path.

`{id}` is a **UUID v7 string** (e.g. `019fd121-eac7-7537-aa3a-ddded8bb0cc8`).

---

# Response

```json
{
  "id": "019fd121-eac7-7537-aa3a-ddded8bb0cc8",
  "name": "Example GmbH",
  "website": "https://...",
  "domain": "example.com",
  "industry": "Software Development",
  "country": "Germany",
  "city": "Berlin",
  "description": "...",
  "company_size": "51-200",
  "company_type": "PRODUCT_COMPANY",
  "logo_url": "https://...",
  "founded_year": "2015",
  "job_count": 3,
  "pinned": false,
  "status": "completed",
  "current_node": null,
  "progress_pct": 100.0,
  "error": null,
  "notes": [
    { "id": 12, "content": "Great culture", "created_at": "..." }
  ],
  "links": [
    {
      "id": 7,
      "url": "https://...",
      "title": "LinkedIn",
      "description": "...",
      "status": "processed",
      "created_at": "..."
    }
  ],
  "intelligence": {
    "overview": { "founded": "2015", "headquarters": "Berlin" },
    "culture_analysis": {},
    "international_analysis": {},
    "career_analysis": {},
    "benefits_analysis": {},
    "visa_analysis": {},
    "technology_analysis": {},
    "recommendation": null,
    "scores": {
      "fit": 88,
      "success": 87,
      "overall": 88,
      "overall_grade": "A+"
    },
    "generated_at": "..."
  },
  "scores": {
    "overall": 88.0,
    "fit": 88.0,
    "success": 87.0,
    "overall_grade": "A+"
  },
  "parent_company_id": null,
  "main_company": null,
  "alias_count": 0,
  "is_alias": false,
  "recruiter_job_count": 0,
  "recruiter_for": [
    {
      "company_id": "...",
      "name": "Acme GmbH",
      "job_count": 2,
      "jobs": [
        { "id": "job-1", "title": "Senior Backend Engineer", "location": "Berlin" },
        { "id": "job-2", "title": "Platform Engineer", "location": "Munich" }
      ]
    }
  ],
  "recruiter_jobs": [
    {
      "id": "job-1",
      "role": "Senior Backend Engineer",
      "location": "Berlin",
      "match": "...",
      "score": "A",
      "fit_score": 84,
      "success_score": 63,
      "overall_score": 76
    }
  ],
  "jobs": [
    {
      "id": "019fd122-...",
      "role": "Principal Python Engineer",
      "location": "Berlin",
      "match": "...",
      "score": "A",
      "fit_score": 90,
      "success_score": 85,
      "overall_score": 88
    }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

---

# Notes

Notes are stored as `company_links` rows whose `title` starts with `note:`.
The detail endpoint returns them parsed as `{ id, content }` (the `note:`
prefix is stripped). Non-note links are returned under `links`.

---

# Main / Alias Relation

Companies may be related to a **main** company (`parent_company_id`). The
detail payload exposes:

| Field               | Type                | Description                                       |
| ------------------- | ------------------- | ------------------------------------------------- |
| `parent_company_id` | string \| null      | The main company's id (null when not an alias)    |
| `main_company`      | `{ id, name }` \| null | The main company's id and name                 |
| `is_alias`          | boolean             | True when `parent_company_id` is set              |
| `alias_count`       | number              | Companies related to this one as aliases          |

Relating is managed via `PUT /api/companies/{id}/main` (see
`relate-company.md`). Relating re-points all non-deleted jobs of the alias and
its own aliases onto the main.

---

# Recruiter Role

When this company acts as a recruiter / staffing agency, the payload exposes
its hiring-client portfolio via the `job_companies` table:

| Field                 | Type                | Description                                              |
| --------------------- | ------------------- | -------------------------------------------------------- |
| `recruiter_job_count` | number              | Jobs this company publishes as a recruiter for clients, excluding jobs where it is also the hiring company |
| `recruiter_for`       | array of `{ company_id, name, job_count, jobs }` | Distinct hiring companies this recruiter publishes for, sorted by job count descending; `jobs` lists the `{ id, title, location }` of the jobs published for that company, sorted by title |
| `recruiter_jobs`      | array of `{ id, role, location, match, score, fit_score, success_score, overall_score }` | Flat, role-sorted list of every job this recruiter publishes for other companies (client jobs), carrying full scores |

A recruiter's job is counted and listed whenever the company appears as
`role="recruiter"` on it — **even when the hiring company is unknown** (the
recruiter still published it for a client). The only jobs excluded are those
where the same company is also the hiring company (its own role, not a client
listing). Non-recruiter companies return `recruiter_job_count: 0`,
`recruiter_for: []` and `recruiter_jobs: []`. The `recruiter_jobs` list is what
the Company Detail drawer renders as its **Jobs listed for clients** section.

---

# Errors

404

Company not found for the given id.

500

Internal server error.

---

# Related Documents

- docs/api/companies/list-companies.md
- docs/ux/features/companies/company-detail.md
- docs/ux/flows/companies/browse-companies.md
