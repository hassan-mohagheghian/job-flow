# Job Tags

## Purpose

Tags let the user apply custom labels to jobs for personal categorization.
Jobs can be tagged with any free-form string. The Tags column shows applied
tags alongside system badges (Dismissed, Visa, Easy Apply). The toolbar
provides a multi-select filter to narrow the list by one or more user-defined
tags.

---

# Related Page

Located in:

- `features/jobs/page.md`
- `features/jobs/job-row.md`

Related:

- `api/jobs/list-jobs.md`

---

# User Goals

The user should be able to:

- See which tags are applied to each job
- Filter the job list by one or more tags
- Tags are user-defined strings (no predefined set)

---

# Tags Column

Each job row shows a Tags column that displays:

1. **User-defined tags** — free-form labels applied by the user
2. **System badges** — auto-populated from job state:
   - Dismissed (red) — if the job is dismissed
   - Visa (blue) — if the job has visa sponsorship
   - Easy Apply (sky) — if the job supports LinkedIn Easy Apply

Tags overflow to a second line when needed (up to 2 visible lines). Content
exceeding 2 lines is truncated with `...` and a downward caret icon.

```text
[python] [remote] [senior]
```

or with system badges:

```text
[visa] [easy apply] [python]
```

Tags are stored as a JSON array of strings on the job. System badges are
derived from the job's `dismissed`, `visa_sponsorship`, and `easy_apply`
flags and are not stored in the tags array.

---

# Tags Filter

The toolbar includes a multi-select tags dropdown.

```text
Tags (2)
  ☑ python
  ☑ remote
  ☐ java
  ☐ senior
```

Selecting multiple tags applies an **intersection** filter: only jobs that
have ALL selected tags are shown. The filter counts as an active filter and
is cleared by the toolbar's Clear action alongside the others.

Note: the filter operates on user-defined tags only. System badges (dismissed,
visa, easy_apply) have their own dedicated filters in the toolbar.

---

# Data Model

Tags are stored in a `jsonb` array column (`tags`) on the `jobs` table. The
column default is `'[]'::jsonb` and it has a GIN index, so tag filters use
JSONB containment (`@>`) instead of substring matching.

```json
["python", "remote", "senior"]
```

No separate tags table exists. Tags are free-form user-defined strings.

System badges (Dismissed, Visa, Easy Apply) are derived from boolean columns
on the jobs table (`deleted`, `visa_sponsorship`, `easy_apply`).

---

# API

## List with tag filter

```
GET /api/jobs/list?tags=python,remote
```

Returns only jobs that contain all specified tags.

## Set tags

```
PUT /api/jobs/{job_id}/tags
{ "tags": ["python", "remote"] }
```

Replaces the existing tags on the job.

---

# Accessibility

- Tag badges use readable text sizes.
- The multi-select filter uses native checkboxes for keyboard accessibility.

---

# Related Documents

- `features/jobs/page.md`
- `features/jobs/job-row.md`
- `api/jobs/list-jobs.md`
