# List Cities API

## Purpose

Returns a paginated list of normalized Cities for the Cities page.

The Cities catalog is the canonical `{city, country}` reference produced by the
`CityNormalizer` during processing. Every job, company and candidate profile
stores a normalized `city` + `country` plus a logical `city_id` pointing into
this table (no cross-context foreign key; referential integrity is enforced at
the application layer).

This endpoint is optimized for browsing, searching and sorting.

The endpoint is read-only.

---

# Endpoint

GET /api/cities/list

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

- City name
- Country
- Original text
- Address

Search is case-insensitive.

---

## Sorting

Supported sort fields

```text
jobs

country

city

created_at
```

Default sort is `jobs desc` (cities with the most linked, non-deleted jobs
first), overriding the usual repo-wide `created_at desc` because job-count is
the primary signal on the Cities page.

Order

```text
asc

desc
```

For `jobs` the sort orders by the number of linked, non-deleted jobs (via a
`LEFT JOIN` against `job.jobs` on `jobs.city_id = cities.id`, filtering
`deleted = 0`), `NULL`/zero last.

---

# Response

```json
{
  "items": [
    {
      "id": "...",
      "city": "Berlin",
      "country": "Germany",
      "original_text": "Berlin, Germany",
      "address": "Berlin, Germany",
      "job_count": 161,
      "updated_at": "...",
      "created_at": "..."
    }
  ],
  "next_cursor": "...",
  "has_more": true,
  "total_items": 240
}
```

---

# Returned Information

Each row contains only the information required by the Cities page.

- `city` — canonical normalized city name
- `country` — canonical normalized country name
- `original_text` — the source location string first seen for this city (nullable)
- `address` — the address/hq string first seen for this city (nullable)
- `job_count` — number of linked, non-deleted jobs for this city

`job_count` is aggregated in the same query (no N+1) via a `LEFT JOIN` against
the jobs table, filtering `deleted = 0`.

---

# Performance Requirements

The endpoint should support:

- Keyset pagination
- Database indexes
- Efficient sorting
- Efficient aggregation of `job_count`

The endpoint must not perform N+1 queries.

---

# Authorization

Users may only retrieve Cities they own.

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

- docs/ux/features/cities/page.md
- docs/domain/cities/cities.md