# Processing Events SSE API

## Purpose

The Processing Events SSE API provides real-time updates for Job ProcessingExecution lifecycle and workflow progress.

The frontend uses this stream to update:

- Processing Queue.
- Workflow Progress UI.
- Execution status.
- Workflow step progress.
- Failure states.
- Queue changes.

This API does not expose internal execution implementation.

The frontend must not depend on:

- TaskIQ task names.
- Worker names.
- LangGraph node names.
- Internal runtime details.

The API exposes user-facing processing events.

---

# Architecture

The event flow:

```text
ProcessingExecution
        |
        v
Background Worker (TaskIQ)
        |
        v
Workflow Engine (LangGraph)
        |
        v
Processing Event Mapper (progress_ops / runner / actions)
        |
        v
Redis pub/sub  (processing:events:{execution_id})
        |
        v
SSE Stream  (/events/processing  → psubscribe "processing:events:*")
        |
        v
Frontend State
```

The Processing Event Mapper converts internal execution changes into stable user-facing events.

---

# Endpoints

## Subscribe Global Processing Events

GET

    /events/processing

Subscribes to the Redis pub/sub pattern `processing:events:*`. One connection
receives events for **all** executions and jobs. This is the stream the frontend
uses.

Response:

Content-Type:

    text/event-stream

The connection remains open until:

- Client disconnects.
- Authentication expires.
- Server shutdown occurs.

## Subscribe Per-Execution Events

GET

    /api/processing/executions/{execution_id}/events

Subscribes to a single execution's channel (`processing:events:{execution_id}`).
This endpoint exists for narrow use cases; the frontend does **not** use it for
the Processing Queue drawer.

## Connection Model

Because the global stream matches the `processing:events:*` pattern, a drawer
listing many executions still needs only **one** SSE connection. Never open one
per-execution connection per listed item — that multiplies connections linearly
with the number of rows. The frontend shares a single global EventSource across
all consumers (see Frontend Synchronization Rules).

---

# Authentication

The SSE connection requires authenticated user context.

Only events belonging to accessible Jobs should be streamed.

Unauthorized executions must not be exposed.

---

# Event Model

All events share a common structure.

Example:

```json
{
  "id": "event-id",
  "type": "event.type",
  "timestamp": "2026-01-01T10:00:00Z",
  "job_id": "job-id",
  "execution_id": "execution-id",
  "target_type": "job",
  "target_id": "job-id",
  "payload": {}
}
```

Fields:

| Field        | Description                            |
| ------------ | -------------------------------------- |
| id           | Unique event identifier                |
| type         | Event type                             |
| timestamp    | Event creation time                    |
| job_id       | Related Job identifier (legacy; may be null) |
| execution_id | Related ProcessingExecution identifier |
| target_type  | Processing target kind: `job` or `company` |
| target_id    | Identifier of the processing target (job id or company UUID) |
| payload      | Event specific data (mirrors `target_type` / `target_id`) |

> Every lifecycle event (`execution.created` / `started` / `completed` /
> `failed` / `cancelled` and `queue.entry.removed`) carries `target_type` and
> `target_id` on both the envelope and the payload. The frontend routes the
> event to the right react-query cache (`jobs-v2-infinite` for jobs,
> `companies-v2-infinite` + `company-detail` for companies) using
> `data.target_type`. Companies fall back to `job_id` semantics via
> `target_id`.

---

# Execution Events

## execution.created

Triggered when a new ProcessingExecution is created.

Purpose:

- Add item to Processing Queue.
- Show queued state.

Payload:

```json
{
  "status": "QUEUED"
}
```

---

## execution.started

Triggered when execution starts processing.

Purpose:

- Move execution from queued state to processing state.

Payload:

```json
{
  "status": "RUNNING",
  "updated_at": "2026-01-01T10:00:00Z"
}
```

---

## execution.completed

Triggered when execution finishes successfully.

Purpose:

- Remove item from Processing Queue.
- Update Job or Company state.
- Frontend refetches the target detail (`['job-detail', jobId]` for jobs,
  `['company-detail', companyId]` for companies) so the new scores + analysis
  block appear live in the detail drawer.

Payload:

```json
{
  "status": "COMPLETED",
  "updated_at": "2026-01-01T10:00:00Z"
}
```

---

## execution.failed

Triggered when execution fails.

Purpose:

- Show failed state.
- Display failure reason.
- Frontend refetches the target detail (`['job-detail', jobId]` /
  `['company-detail', companyId]`) to clear stale analysis data.

Payload:

```json
{
  "status": "FAILED",
  "message": "Unable to fetch source",
  "updated_at": "2026-01-01T10:00:00Z"
}
```

---

## execution.cancelled

Triggered when execution is cancelled.

Payload:

```json
{
  "status": "CANCELLED",
  "updated_at": "2026-01-01T10:00:00Z"
}
```

---

# Queue Events

## queue.entry.removed

Triggered when a queue entry is removed.

Purpose:

- Remove item from Processing Queue UI.
- Keep Job history unchanged.

Payload:

```json
{
  "status": "FAILED"
}
```

---

# Workflow Step Events

Workflow steps represent user-facing processing stages.

They are independent from internal LangGraph nodes.

The combined Job Processing workflow exposes 13 user-facing steps spanning both
phases: `load_job`, `collect_sources`, `fetch_sources`, `extract_content`,
`build_context`, `validate_context`, `persist_context`, `analyze`,
`extract_skills`, `score`, `recommend`, `summarize`, `persist`. Internal nodes
(`execution_failed`, `context_ready`, `analysis_ready`, `load_context`,
`prepare_profile`) never emit visible step events.

Example:

Internal:

```text
analyze
```

Public:

```text
Analyze Job
```

---

# workflow.step.started

Triggered when a visible workflow step starts.

Payload:

```json
{
  "status": "processing",
  "step": {
    "id": "fetch_content",
    "title": "Fetch Content",
    "status": "processing",
    "displayable": true
  }
}
```

---

# workflow.step.progress

Triggered when step progress changes.

Payload:

```json
{
  "status": "processing",
  "step": {
    "id": "fetch_content",
    "title": "Fetch Content",
    "status": "processing",
    "progress": 60,
    "displayable": true
  }
}
```

---

# workflow.step.completed

Triggered when a workflow step finishes.

Payload:

```json
{
  "status": "completed",
  "step": {
    "id": "fetch_content",
    "title": "Fetch Content",
    "status": "completed",
    "displayable": true
  }
}
```

---

# workflow.step.failed

Triggered when a workflow step fails.

Payload:

```json
{
  "status": "failed",
  "step": {
    "id": "fetch_content",
    "title": "Fetch Content",
    "status": "failed",
    "displayable": true,
    "error": {
      "code": "SOURCE_FETCH_FAILED",
      "message": "Primary source unavailable"
    }
  }
}
```

---

# Nested Step Updates

A workflow step may contain child steps.

Example:

```text
Fetch Content

    Primary URL

    Company Website

    Additional Links
```

The `step` payload is the full `WorkflowStep` model, so child statuses and
progress are carried inside the parent step's `children` array — even when a
child transition does not emit its own event.

Payload:

```json
{
  "status": "processing",
  "step": {
    "id": "fetch_content",
    "children": [
      {
        "id": "primary_url",
        "title": "Primary URL",
        "status": "completed"
      },
      {
        "id": "company_url",
        "title": "Company Website",
        "status": "processing",
        "progress": 40
      }
    ]
  }
}
```

---

# Frontend Synchronization Rules

The frontend maintains a local execution state.

Initial state:

```text
REST API snapshot
```

Continuous updates:

```text
SSE events
```

A single shared `EventSource` (module singleton in
`shared/api/processingEvents.ts`) fans events out to every
consumer, so all components — the Processing Queue drawer and the jobs-list
status hook — share one connection regardless of how many executions are visible.

The EventSource connects **directly to the backend origin** when
`NEXT_PUBLIC_API_URL` is baked in at build time (local dev, `npm run dev`),
**not** through the Next.js rewrite proxy. When `NEXT_PUBLIC_API_URL`
is empty (prebuilt docker image used by terraform, where `NEXT_PUBLIC_*`
cannot be injected at container runtime), the client falls back to the
same-origin relative URL `/events/processing`, which `next.config.ts`
`rewrites()` proxies to `${BACKEND_URL}` (the backend container in docker).
The proxied response carries `Cache-Control: no-cache, no-transform` so the
proxy must not compress it: compression buffers SSE frames, and gzip-accepting
browsers would otherwise receive nothing until the buffer flushes (which looks
exactly like "processing works but the UI never updates live").
The backend also emits `: ping` keepalive comments so intermediaries never
idle-close the stream. Set `NEXT_PUBLIC_API_URL` to the backend
origin (defaults to `http://localhost:5000`).

Workflow step events are applied directly to the in-memory workflow tree via a
local merge (`mergeWorkflowStep`), so step/child progress renders instantly
without a REST round-trip. REST is only re-fetched when needed: on drawer open,
on `execution.created`, and on lifecycle/queue changes. In addition,
`useProcessingEvents.ts` invalidates the target detail react-query query
(`['job-detail', jobId]` or `['company-detail', companyId]` depending on
`data.target_type`) on `execution.completed` and `execution.failed`, so the
detail drawer refetches and shows the persisted scores + analysis block live.

Flow:

```text
Open Processing Queue
        |
        v
GET /api/processing/queue
        |
        v
GET /api/processing/executions/{id}
        |
        v
Subscribe SSE  (one shared EventSource to the backend origin, e.g. http://localhost:5000/events/processing)
        |
        v
Apply events  (workflow.step.* → merge tree; execution.* / queue.* → refresh snapshot)
        |
        v
Update UI
```

---

# Event Ordering

Events contain:

- timestamp
- unique identifier

Frontend should process events in order.

If an event gap is detected:

1. Fetch execution snapshot again.
2. Replace local state.
3. Continue consuming SSE events.

---

# Retry Behavior

Retry creates a new ProcessingExecution.

The frontend receives:

```text
execution.created
```

for the new execution.

The previous failed execution remains unchanged.

---

# Cancellation Behavior

When cancellation succeeds:

Frontend receives:

```text
execution.cancelled
```

The Processing Queue entry is removed.

---

# Empty State

When no active executions exist:

- SSE connection remains open.
- No event is emitted.

---

# Related Documents

- docs/api/processing/get-processing-queue.md
- docs/api/processing/get-processing-execution.md
- docs/domain/processing/processing-execution.md
- docs/domain/processing/events.md
- docs/domain/processing/workflow-progress.md
- docs/architecture/runtime/workflow-progress.md
- docs/ux/features/jobs/processing-queue.md
- docs/ux/features/jobs/workflow-progress.md
- docs/workflows/job-processing.md (realized trace-through + current two-path note)
