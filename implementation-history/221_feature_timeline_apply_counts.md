# Prompt 221 - Per-Day Apply Counts in Jobs Timeline

## Objective
Show, for each day in the Jobs Created Timeline, how many of that day's jobs the user has actually applied to — rendered as a parenthesized count with a hover tooltip — so strong application days are visible at a glance. (`apply` = tracking funnel at or past `applied`, not the AI recommendation.)

## Current State
- Backend: `repo.count_created_by_day` (`sa_job_repository.py:207`) groups non-deleted jobs by `substr(created_at,1,10)`; `GET /api/jobs/timeline` (`jobs_v2_router.py:596`); at most one application per job (`docs/domain/overview.md`); `ApplicationModel` (`applications/.../application_model.py:29`) with user-scoped `statuses_by_job_ids` (`sa_application_repository.py:53`); `case` already imported in `sa_job_repository.py:7`.
- Frontend: `JobTimeline.tsx:65` renders day + bold count in a `w-24` panel; global `TooltipProvider` in `app/providers.tsx:17`; `JobTimeline.test.tsx` exists (Radix requires provider wrapping in tests).
- Docs: `docs/ux/features/jobs/job-created-timeline.md`, `docs/api/jobs/job-created-timeline.md`, `docs/api/API.md:137`.

## Changes
1. Backend: `count_created_by_day` outer-joins `application.applications` (job_id + user_id match; method-level import following the companies→jobs precedent) with `sum(case(status in applied/interview/offer/accepted))` → `{date, count, apply_count}`; router returns `apply_total` sum; schemas gain `apply_count: int = 0` / `apply_total: int = 0`. Rejected/withdrawn/expired and application-less jobs contribute 0.
2. Frontend: day row shows count + `(N apply)` muted sub-line when positive (count-only otherwise); row wrapped in shared `Tooltip`: `{apply} of {count} jobs added {day} have been applied to.` / `Nothing applied from {day} yet.`
3. Types updated; `JobTimeline.test.tsx` extended (parens, both tooltips, provider wrapper); backend timeline tests extended (applied vs preparing, interview-counts/rejected-does-not, deleted exclusion, empty).
4. Docs: timeline wireframe + field descriptions in the three docs above.

## Testing Requirements
- Backend timeline tests + `./scripts/docker-test.sh backend`; frontend `JobTimeline.test.tsx` + `tsc --noEmit` clean for touched files.
- No migration (read-only aggregation over existing columns).

## Constraints
- Respect AGENTS.md rules 2, 3 (single conditional-aggregate query — no N+1, no raw SQL), 10, 11, 13 (wireframe + tooltip behavior documented), 18 (Docker tests only).
- Counts stay user-scoped; the join cannot duplicate jobs (≤1 application per job).
