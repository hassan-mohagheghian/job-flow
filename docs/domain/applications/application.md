# Application (bounded context)

## Purpose

This document describes the **Applications** bounded context: the application record
for a job and its related artifacts. It is the backend behind the Job Application
Workspace (`/jobs/{job_id}/application`).

## Concepts

| Concept | Entity | Description |
| ------- | ------ | ----------- |
| Application | `Application` | The aggregate root. Represents a user's application for a single job. |
| Status event | `ApplicationStatusEvent` | One node of the status timeline: the application entered a `status` at a `changed_at` time. |
| Follow-up | `ApplicationFollowUp` | A scheduled/recorded touch-point (date, note, completion). Minimal, not a CRM. |
| Document | `ApplicationDocument` | A versioned generated artifact (tailored resume, cover letter) stored as markdown. |

## Application Status

`ApplicationStatus` is a closed set of strings:

| Value | Meaning |
| ----- | ------- |
| `seen` | Default on creation; the job has been seen. |
| `preparing` | The user is preparing (generating plan/documents). |
| `ready_to_apply` | Artifacts are ready. |
| `applied` | The user applied (may set `applied_at`). |
| `interview` | Interviewing with the company. |
| `offer` | Received an offer. |
| `accepted` | Offer accepted / hired. |
| `rejected` | Outcome rejected. |
| `withdrawn` | The user withdrew. |
| `expired` | Posting-side terminal: the job is no longer accepting applications. |

## Document Types

`DocumentType`:

| Value | Execution type |
| ----- | -------------- |
| `tailored_resume` | `application_resume` |
| `cover_letter` | `application_cover_letter` |

The application documents are produced by the Processing bounded context
(`docs/ai/application-intelligence.md`) and persisted here by its workflow persist
node. A skill-gap roadmap for an application lives in the Roadmaps context
(`docs/ai/roadmap-generation.md`).

## Aggregates and Cross-Context References

- The `Application` is the aggregate root; it **owns** its follow-ups, documents
  and status-timeline events.
- `job_id` is a **logical reference** to the Jobs context — a plain column, **no
  FK**, no `ondelete` cascade (AGENTS.md rule 15). Referential integrity is enforced
  by the application layer / repositories.
- Database schema: `application` with tables `applications`,
  `application_status_timeline`, `application_follow_ups`, `application_documents`.

## Status Timeline

Every status transition is recorded as an `application_status_timeline` row
(`status`, `changed_at`). On application creation a `seen` event is
written with `changed_at = created_at`. Each status change appends a new event;
the time defaults to **now** but can be overridden (`timeline_at` on the PATCH
body) or corrected/removed later via the timeline endpoints. The application's
`status` field mirrors the latest timeline entry.

## Business Rules

- An application is created explicitly for a job (`POST /api/applications {job_id}`),
  defaulting to status `seen`. There is at most one application per job
  (`get_by_job_id`).
- Documents are **versioned**: each successful generation writes a new row (higher
  `version`); edits bump `version`.
- Hard delete: deleting an application removes its follow-ups, documents and its
  generation executions.
- Deleting a **job** cascades to its application and children (job-delete flow, rule 8).

## Domain Events

See `docs/domain/applications/events.md` for the full EDD catalog.

# Related Documents

- `docs/api/applications/` — API reference.
- `docs/ai/application-intelligence.md` — generation workflow.
- `docs/ux/features/applications/` — UI specs.
