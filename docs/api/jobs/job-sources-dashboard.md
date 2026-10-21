# Job Sources Dashboard (backend)

Feature: per-source job listing aggregates powering the Dashboard
(`docs/ux/features/dashboard/page.md`). Implemented in the **jobs** bounded
context; all endpoints are user-scoped (repo `user_id` scoping via
`get_job_repo`) and count only **non-deleted** jobs.

## Schema (alembic `job_009_add_job_sources`)

- New table `job.job_sources`: `id` (uuid), `user_id` (indexed),
  `name`, `canonical_url`, `normalized_domain`, `is_active` (int 0/1,
  default 1), `created_at`/`updated_at` (Text ISO). Unique
  `(user_id, normalized_domain)` + index on `normalized_domain`.
  No FK from `job.jobs.source_site_id` (logical reference per repo rule 15 —
  same schema but mirrors the existing `company_id` convention).
- `job.jobs.source_site_id` (String36, nullable, indexed
  `idx_jobs_source_site_id`) — the resolved source site.
  The legacy free-text `source` column ("web"/"cli"/"api"/"provider") is
  untouched and still describes the *ingestion channel*, not the board.
- Backfill: migration assigns `source_site_id` for historical rows in
  resumable batches of 500 (`url IS NOT NULL AND deleted = 0 AND
  source_site_id IS NULL`), resolving the canonical domain of each job URL
  and get-or-creating the source row per user. Rows whose URL yields no
  canonical domain (missing/invalid URL) stay `NULL` → dashboard "Unknown".

## Source identification rules (`jobs/domain/services/job_source_rules.py`)

Pure functions:

- `extract_hostname(url)` — accepts `http(s)://host/...`, bare `host`,
  `www.host`; returns lowercased hostname without port, or `None` if
  unparseable / empty.
- `canonicalize_domain(host)` — strips leading `www.` and trailing dots,
  drops port/fragment leftovers, then applies the known-alias suffix map
  (`KNOWN_BOARD_SUFFIXES`): multi-tld boards unify to their registrable
  identity (e.g. `de.indeed.co.uk` → `indeed.com`, `merojob.com.np` →
  `merojob.com`). Overmatching is avoided: only
  listed suffixes canonicalize; unknown TLD variants stay their own source.
  Output `None` when empty.
- `display_name_for_domain(domain)` — title-cases the registrable label
  (`indeed.com` → `Indeed.com`).
- Full duplex: `resolve_source(url) -> str | None` = the canonical domain of
  a job URL. Source identity is deliberately separate from job URLs and any
  external job identifiers (fragment dedupe rules in `job_url_rules.py`).

## Ingestion integration

`SQLAlchemyJobRepository.create_job` resolves the source from the supplied
`job_post_url` and links the job by get-or-creating
`job.job_sources (user_id, normalized_domain)` inside the same
session/transaction (nested savepoint → IntegrityError-safe, duplicate
safe). No change to deduplication (fragment rules) and hard-delete
behavior; `delete_by_id` only touches `job_analysis`/`summaries` tables —
sources are intentionally never garbage-collected on job deletion (counts
naturally drop; empty `is_active` sources remain listed).

## Endpoints (all under the existing `/api/jobs` jobs-v2 router)

### GET /api/jobs/sources/stats

```json
{
  "total_jobs": 1258,
  "total_sources": 14,
  "active_sources": 12,
  "unknown_jobs": 23
}
```

- `total_jobs` — non-deleted listings of the user (denominator used by the
  chart).
- `total_sources` — distinct non-null `source_site_id` values for those jobs.
- `active_sources` — sources among those with `is_active = 1`. (Deactivation
  is a future admin affordance; today active == listed sources.)
- `unknown_jobs` — listings with `source_site_id IS NULL`.

### GET /api/jobs/sources/distribution

```json
{
  "items": [
    {"id": "…", "name": "Indeed.com", "domain": "indeed.com", "job_count": 412}
  ],
  "other_count": 182,
  "unknown_count": 23
}
```

- Groups by source with counts in one query (`GROUP BY` + outer join,
  no N+1, no per-source count queries); sources beyond the top
  `limit` (query, default 5) fold into `other_count`;
  `unknown_count` counts `source_site_id IS NULL` jobs.

### GET /api/jobs/sources

Query: `page` (default 1), `page_size` (default 10, max 100), `query`
(search on name + normalized_domain, ILIKE prefix match), `sort`
(`job_count` default | `name` | `last_activity`), `order` (`desc` default |
`asc`).

```json
{
  "items": [
    {
      "id": "…",
      "name": "Indeed.com",
      "canonical_url": "https://www.indeed.com",
      "normalized_domain": "indeed.com",
      "is_active": true,
      "job_count": 412,
      "last_activity": "2026-10-14T08:25:00.000Z",
      "last_activity_display": "Oct 14"
    }
  ],
  "pagination": {"page": 1, "page_size": 10, "total_items": 14, "total_pages": 2}
}
```

- `last_activity` = `max(jobs.created_at)` for the source (ISO; `last_activity_display`
  omitted when null). `canonical_url` persisted at row creation (host prefix
  of the first URL that created it).
- Invalid `sort`/`order`/page values → 422.
- The client defaults to 10 rows and exposes a per-page selector in steps of
  10 (10 / 20 / 30 / … / 100; changing it resets to page 1); the server caps
  `page_size` at 100.

### GET /api/jobs/recommendations/distribution

Counts of the current user's **non-deleted** jobs grouped by the
`recommendation` column of their `job_analysis` row (left join, so jobs
without an analysis land in `none`; legacy/unknown labels also fold into
`none`). Only non-empty buckets are returned; `total` is always the full
non-deleted job count.

```json
{
  "items": [
    { "recommendation": "apply", "count": 12 },
    { "recommendation": "consider", "count": 7 },
    { "recommendation": "skip", "count": 3 }
  ],
  "total": 29
}
```

`recommendation` ∈ `apply | consider | skip | none`. Rendered as the
"Jobs by recommendation" doughnut next to the source distribution
(semantic colors: green / amber / red / gray).

## Performance

- All widgets rely on one indexed aggregation each: `idx_jobs_source_site_id`
  join `idx_jobs_created_at`-indexed grouping; no full-table loads into
  Python; no per-source queries (one `GROUP BY` per endpoint).
- Measured on dev data (1,258 jobs, 1258 rows `EXPLAIN ANALYZE` numbers in
  the implementation report): each aggregate runs in low single-digit ms.
- No materialized view/counter table — live aggregation is cheap at this
  dataset scale; revisit if `job.jobs` grows into the millions.

## Testing

- `tests/jobs/domain/test_job_source_rules.py` — hostname/canonicalization
  (www, ports, trailing dots, aliases, unknown TLDs, invalid URLs).
- `tests/jobs/infrastructure/…/testjob_source_aggregates.py` — counts,
  pagination, search, sort, empty, deletes affecting counts.
- `tests/jobs/presentation/api/test_jobs_sources_api.py` — response shapes,
  404-ish/auth behavior, validation errors, user isolation
  (count only current user's rows).
