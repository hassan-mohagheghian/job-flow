# Opportunity

## What

An `Opportunity` (`opportunities` context, schema `opportunity`) is the aggregate root for an inbound recruiting message. It starts from a pasted message/email — which may be a full JD, a short recruiter note, a bare company name, or a bare job link — and is progressively enriched, resolved against existing entities, and evaluated against the canonical candidate profile.

It never replaces the JD-first Job pipeline; it reuses it. An opportunity may link to an existing `job.jobs` row or `company.companies` row, but it never creates jobs, companies, or skills.

## Storage

- `opportunity.opportunities` — source/message metadata (`source`, `source_message_id`, sender, `received_at`, subject, `raw_content`), extracted URLs, `content_hash` (dedupe), `extracted` JSON, logical `company_id` / `job_id` (plain columns, no FK — AGENTS.md rule 15), denormalized `company_name` / `job_title`, lifecycle `status`, `evaluation_status` (`pending` / `complete`), nullable fit/success/overall + recommendation, `evaluation` JSON, deterministic `application_path` JSON, `next_action`.
- `opportunity.opportunity_evaluations` — immutable per-evaluation snapshot (FK within the schema only), newest first; reprocessing appends, never overwrites.

## Lifecycle

`new` → `extracted` → `enriching` → `evaluated` / `needs_info` → `ready_to_apply` → `applied` → `replied` / `interview` / `rejected` / `closed`.

- Pipeline transitions: create sets `new`; extract sets `extracted`; resolution sets `enriching`; evaluation sets `evaluated` (scored but no actionable path), `ready_to_apply` (scored + actionable path), or `needs_info` (insufficient information, scores stay `null`).
- User transitions follow the funnel above; terminal states are `rejected` / `closed`. Invalid transitions are rejected with 422.

## Extraction

`opportunity.extract` (one structured LLM call, versioned prompt/schema) returns partial fields only. Every field carries a state: `known` / `unknown` / `inferred` / `needs_verification`. Missing information is never fabricated.

## Entity resolution

- Job: extracted URLs are matched with the existing `find_duplicate_job` URL rules; the first match links the opportunity. No jobs are created.
- Company: exact normalized-name / exact-domain matches against `list_for_matching()` link the opportunity. No companies are created on weak evidence.
- Skills: required-skill names are compared against the candidate's own skills (exact, case-insensitive). `resolve_skill` is never used — no skills are created.
- Duplicates: same `source_message_id` or same `content_hash` returns the existing opportunity instead of creating a new one.

## Evaluation

`opportunity.evaluate` (one structured LLM call) scores fit/success against the canonical candidate profile (`build_candidate_profile_text`, falling back to resume/LinkedIn text) plus enabled `SHARED` + `JOB` rules and the linked job/company summaries. Deterministic post-processing reuses the job-scoring helpers: `overall = round(fit × 0.6 + success × 0.4)`, recommendation `apply ≥ 80` / `consider ≥ 60` / else `skip`. With insufficient information the evaluation stays `pending` with `missing_information` and a research next action.

## Application path

Derived deterministically from available information, never invented: extracted job URL → apply via posting; known sender → reply to sender / ask for JD or location; otherwise research first.

# Related Documents

- `docs/domain/opportunities/events.md`
- `docs/api/opportunities/README.md`
- `docs/ux/features/opportunities/page.md`
