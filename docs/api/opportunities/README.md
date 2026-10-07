# Opportunities API

## Purpose

The Opportunities API exposes the inbound-opportunity pipeline: store a pasted message, extract/resolve/evaluate it, link existing jobs/companies, move it along the funnel, and delete it. It lives in the Opportunities bounded context router (`/api/opportunities`) — per-context routers (AGENTS.md rule 10).

Processing is synchronous in phase one (no TaskIQ/SSE): `POST .../process` runs extract → resolve → evaluate and returns the updated detail.

## Overview

| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/api/opportunities` | Create from a manual message (201; duplicate content returns the existing row with `duplicate: true`, 200). |
| GET | `/api/opportunities` | List newest first; filters `status`, `source`, `query`; `limit`/`offset`. |
| GET | `/api/opportunities/{id}` | Full detail incl. extracted, evaluation, application path, evaluations history (404 when missing). |
| POST | `/api/opportunities/{id}/process` | Run extract → resolve → evaluate (404 when missing; 502 when the AI call fails). |
| POST | `/api/opportunities/{id}/reprocess` | Same as process; appends a new evaluation snapshot. |
| PATCH | `/api/opportunities/{id}/links` | Link/unlink existing `job_id` / `company_id` (404 when the target is unknown). |
| PATCH | `/api/opportunities/{id}/status` | Move along the funnel (invalid transitions → 422). |
| DELETE | `/api/opportunities/{id}` | Hard-delete the opportunity and its evaluations (204). |

## Create Opportunity

`POST /api/opportunities` — body `{ "source": "manual", "source_message_id"?, "sender"?, "sender_email"?, "received_at"?, "subject"?, "raw_content" }`.

`source` is one of `manual` / `gmail` / `linkedin` (only manual ingestion exists in phase one; the vocabulary is reserved for future integrations). `raw_content` must be non-empty.

## Errors

| Code | Condition |
| ---- | --------- |
| 400 | Malformed request. |
| 404 | Opportunity / linked job / company not found. |
| 422 | Validation error (empty content, unknown source, invalid status transition). |
| 502 | The AI extraction/evaluation call failed. |

# Related Documents

- `docs/domain/opportunities/opportunity.md`
- `docs/ux/features/opportunities/page.md`
