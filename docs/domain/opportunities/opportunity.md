# Opportunity

## What

An `Opportunity` (`opportunities` context, schema `opportunity`) is the aggregate root for an inbound recruiting message. It starts from a pasted message/email — which may be a full JD, a short recruiter note, a bare company name, or a bare job link — and is progressively enriched, resolved against existing entities, and evaluated against the canonical candidate profile.

It never replaces the JD-first Job pipeline; it reuses it. An opportunity may link to an existing `job.jobs` row or `company.companies` row, but it never creates companies or skills. **One deliberate exception:** `move_to_job` (see [Move to Job](#move-to-job)) creates a single `job.jobs` row on explicit user action.

## Storage

- `opportunity.opportunities` — source/message metadata (`source`, `source_message_id`, sender, `received_at`, subject, `raw_content`), extracted URLs, nullable `base_url` (the canonical sourcing page, e.g. the LinkedIn post — validated http(s); folded into the extracted URLs for resolution), `content_hash` (dedupe), `extracted` JSON, logical `company_id` / `job_id` (plain columns, no FK — AGENTS.md rule 15), denormalized `company_name` / `job_title`, lifecycle `status`, `evaluation_status` (`pending` / `complete`), nullable fit/success/overall + recommendation, `evaluation` JSON, deterministic `application_path` JSON, `next_action`.
- `opportunity.opportunity_evaluations` — immutable per-evaluation snapshot (FK within the schema only), newest first; reprocessing appends, never overwrites.
- `opportunity.opportunity_notes` — follow-up trail: titled, timestamped notes recording later messages and new details for reassessment. Notes are immutable (add/delete, no edit); `author` is the display name stamped server-side from the authenticated user so it cannot be spoofed; rows are `user_id`-scoped like every other table.
- `opportunity.opportunity_links` — user-saved source links: `title` (optional), `url` (validated http(s)), `FK` to the aggregate within the schema, `user_id`-scoped. Links are immutable (add/delete, no edit), mirroring the notes pattern.

## Lifecycle

`new` → `extracted` → `enriching` → `evaluated` / `needs_info` → `ready_to_apply` → `applied` → `replied` / `interview` / `rejected` / `closed`.

- Pipeline transitions: create sets `new`; extract sets `extracted`; resolution sets `enriching`; evaluation sets `evaluated` (scored but no actionable path), `ready_to_apply` (scored + actionable path), or `needs_info` (insufficient information, scores stay `null`).
- User transitions follow the funnel above; terminal states are `rejected` / `closed`. Invalid transitions are rejected with 422.

## Dismiss

A `dismissed` flag (0/1) hides an opportunity from the default list without deleting it; `Show dismissed` reveals dismissed rows. Dismissing with a reason records it as a follow-up note titled `Dismissed`. Undismissing only clears the flag. Managed via `PUT /api/opportunities/{id}/dismissed`, mirroring the jobs dismiss pattern. Like jobs pin/dismiss flags, it emits no domain event.

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

## Notes, links & base URL

Three user-owned attachments complement the AI extraction:

- **Follow-up notes** (`opportunity.opportunity_notes`, see Storage) record later conversations and details.
- **User links** (`opportunity.opportunity_links`) store titled URLs the user wants to keep with the opportunity — a LinkedIn post, a careers page, a company about page. Managed via `POST /api/opportunities/{id}/links` and `DELETE /api/opportunities/links/{link_id}`.
- **Base URL** (`base_url`, nullable) marks the canonical page the opportunity came from — set via `PATCH /api/opportunities/{id}/base-url`. It feeds resolution: it is folded into the opportunity's extracted URLs, so it participates in job duplicate matching like any extracted URL. An empty value clears it.

All three are user content: URLs must be valid http(s) (422 otherwise), and they are deleted together with the opportunity.

## Move to Job

An evaluated, scored opportunity can be moved into the Jobs bounded context on explicit user action (`POST /api/opportunities/{id}/move-to-job`, `OpportunityService.move_to_job`). Rules:

- **Precondition**: `evaluation_status = complete` and an overall score exists. Unevaluated opportunities are rejected with 422.
- **Create-or-link**: the extracted job URLs are matched with `find_duplicate_job`; a match only links the existing job. With no match, a new `job.jobs` row is created (status `imported`, never queued for processing) and kept consistent with the opportunity's evaluated state:
  - `fit_score` / `success_score` / `overall_score` copied from the evaluation,
  - `role` / `title` from the extracted role title, `company` / `company_id` from the linked company,
  - the raw inbound message stored as the job's JD note (`notes`), with the extracted URL added as a link,
  - `source = "opportunity"` so the origin of the job remains traceable.
- **Postcondition**: the opportunity keeps its funnel status, with `job_id` / `job_title` set. The action is idempotent: a previously moved opportunity is returned unchanged with no duplicate job.
- No URL in the extraction → 422 ("nothing to link or create").

# Related Documents

- `docs/domain/opportunities/events.md`
- `docs/api/opportunities/README.md`
- `docs/ux/features/opportunities/page.md`
