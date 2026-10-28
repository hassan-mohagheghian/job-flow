# Opportunities API

## Purpose

The Opportunities API exposes the inbound-opportunity pipeline: store a pasted message, extract/resolve/evaluate it, link existing jobs/companies, move it along the funnel, and delete it. It lives in the Opportunities bounded context router (`/api/opportunities`) — per-context routers (AGENTS.md rule 10).

Processing is synchronous in phase one (no TaskIQ/SSE): `POST .../process` runs extract → resolve → evaluate and returns the updated detail.

## Overview

| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/api/opportunities` | Create from a manual message (201; duplicate content returns the existing row with `duplicate: true`, 200). |
| GET | `/api/opportunities` | List newest first; filters `status`, `source`, `query`, `dismissed`; `limit`/`offset`. |
| GET | `/api/opportunities/{id}` | Full detail incl. extracted, evaluation, application path, evaluations history, saved links and `base_url` (404 when missing). |
| POST | `/api/opportunities/{id}/process` | Run extract → resolve → evaluate (404 when missing; 502 when the AI call fails). |
| POST | `/api/opportunities/{id}/reprocess` | Same as process; appends a new evaluation snapshot. |
| PATCH | `/api/opportunities/{id}/links` | Link/unlink existing `job_id` / `company_id` (404 when the target is unknown). |
| PATCH | `/api/opportunities/{id}/status` | Move along the funnel (invalid transitions → 422). |
| POST | `/api/opportunities/{id}/notes` | Add a follow-up note (201; body `{ "title"?, "content" }`, author stamped from auth). |
| DELETE | `/api/opportunities/notes/{note_id}` | Delete a follow-up note (204). |
| POST | `/api/opportunities/{id}/links` | Add a user-saved source link (201; body `{ "title"?, "url" }`; URL must be http(s)). |
| DELETE | `/api/opportunities/links/{link_id}` | Delete a user-saved source link (204). |
| PATCH | `/api/opportunities/{id}/base-url` | Set or clear the canonical sourcing base URL (e.g. a LinkedIn post); body `{ "base_url": "<url>" }` — `null` / `""` clears it. |
| PUT | `/api/opportunities/{id}/dismissed` | Dismiss / undismiss (`{ "dismissed", "note"? }`; a dismiss note is saved to the follow-up trail as `Dismissed`). |
| POST | `/api/opportunities/{id}/move-to-job` | Move an evaluated, scored opportunity into Jobs: link the matching existing job or create one from the extracted URL (scores + JD note carried over). 404 when missing; 422 when unevaluated or no URL. |
| DELETE | `/api/opportunities/{id}` | Hard-delete the opportunity and its evaluations (204). |

## Create Opportunity

`POST /api/opportunities` — body `{ "source": "manual", "source_message_id"?, "sender"?, "sender_email"?, "received_at"?, "subject"?, "raw_content", "base_url"?, "notes"?, "links"? }`.

`source` is one of `manual` / `gmail` / `linkedin` (only manual ingestion exists in phase one; the vocabulary is reserved for future integrations). `raw_content` must be non-empty. Optional user content accepted at create time: `base_url` (canonical sourcing page, http(s)), `notes` (list of `{ "title"?, "content" }`) and `links` (list of `{ "title"?, "url" }`).

## Errors

| Code | Condition |
| ---- | --------- |
| 400 | Malformed request. |
| 404 | Opportunity / linked job / company / link not found. |
| 422 | Validation error (empty content, unknown source, invalid status transition, move-to-job before evaluation or without a URL, invalid link or base URL — must be http(s)). |
| 502 | The AI extraction/evaluation call failed. |

# Related Documents

- `docs/domain/opportunities/opportunity.md`
- `docs/ux/features/opportunities/page.md`
