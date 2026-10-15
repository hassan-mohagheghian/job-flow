# Jobs Created Timeline

`GET /api/jobs/timeline`

Returns the number of **non-deleted** jobs created per calendar day, newest
first, plus how many of each day's jobs the user has applied to.
Grouped by the day portion of `created_at` (a `Text` ISO column via
`substr(created_at, 1, 10)`). Display-only; independent of list filters.

```json
{
  "days": [ { "date": "2026-08-19", "count": 3, "apply_count": 2 } ],
  "total": 8,
  "apply_total": 5
}
```

- `days` — newest first; `date` is `YYYY-MM-DD`, `count` is that day's jobs,
  `apply_count` is that day's jobs with an application at or past `applied`
  (`applied`, `interview`, `offer`, `accepted`).
- `total` — sum of all `count`s; `apply_total` — sum of all `apply_count`s.
- Deleted jobs (`deleted == 1`) are excluded. Jobs with `NULL` `created_at` are
  excluded. Jobs with no (or only pre-`applied`) application contribute 0.
- Single conditional-aggregate query (outer join on job + user, no N+1).

## Repository

`SQLAlchemyJobRepository.count_created_by_day()` groups by
`func.substr(JobModel.created_at, 1, 10)` and orders by the **same** SQL
expression object (`day.desc()`), reusing it for both `GROUP BY` and `ORDER BY`
— required by PostgreSQL to avoid a `GroupingError`. The `apply_count` is a
`sum(case(application status in applied/interview/offer/accepted))` over an
outer join matching job **and** user, so counts stay user-scoped (at most one
application per job, so day counts are unaffected).

## Related

- `docs/api/API.md` — endpoint overview.
- `docs/ux/features/jobs/job-created-timeline.md` — the frontend side panel.