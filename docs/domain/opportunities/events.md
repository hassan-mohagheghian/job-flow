# Opportunity Domain Events (EDD Catalog)

## Purpose

Catalog for domain events emitted by the **Opportunities** bounded context. Events are immutable facts (dataclasses extending `shared.domain.domain_event.DomainEvent`) defined in `apps/backend/opportunities/domain/events.py`.

## EDD Approach (Incremental)

Per AGENTS.md rule 16: events are defined, emitted and documented; services emit through the context's event publisher port (`opportunities/domain/event_publisher.py`); the default implementation is an **in-memory collector** — no Redis, no SSE, no outbox. Emission is best-effort. A real transport is wired in a dedicated later phase.

### Event flow (current — in-memory)

```mermaid
flowchart LR
    A[OpportunityService] -->|emit| P[OpportunityEventPublisher port]
    P -->|default| C[InMemoryEventCollector]
    C -->|read / assert| T[Tests + callers]
    P -.->|future transport phase| R[(Redis / Outbox / SSE)]
```

## Event Catalog

### `opportunity.created`

- **Event**: `OpportunityCreated`
- **Trigger**: `OpportunityService.create_manual` persists a new opportunity.
- **Payload**: `opportunity_id`, `source`.
- **Fires when**: an inbound message is stored (`new`). Duplicate content returns the existing row and fires nothing.
- **Consumers**: none yet.

### `opportunity.extracted`

- **Event**: `OpportunityExtracted`
- **Trigger**: `OpportunityService.process` / `reprocess` stores the `opportunity.extract` result.
- **Payload**: `opportunity_id`, `has_role`, `has_company`, `url_count`.
- **Fires when**: the message moves `new` → `extracted`.
- **Consumers**: none yet.

### `opportunity.linked`

- **Event**: `OpportunityLinked`
- **Trigger**: resolution links an existing job/company, or `set_links` links/unlinks one manually.
- **Payload**: `opportunity_id`, `job_id`, `company_id`.
- **Fires when**: the opportunity moves to `enriching` with at least one link (or links change).
- **Consumers**: none yet.

### `opportunity.evaluated`

- **Event**: `OpportunityEvaluated`
- **Trigger**: `OpportunityService.process` / `reprocess` completes evaluation (scored or pending).
- **Payload**: `opportunity_id`, `status`, `overall_score`, `recommendation`.
- **Fires when**: an evaluation snapshot is appended (`evaluated`, `ready_to_apply`, or `needs_info`).
- **Consumers**: none yet.

### `opportunity.status.changed`

- **Event**: `OpportunityStatusChanged`
- **Trigger**: `OpportunityService.set_status`.
- **Payload**: `opportunity_id`, `status`.
- **Fires when**: the user moves the opportunity along the funnel.
- **Consumers**: none yet.

### `opportunity.note.added`

- **Event**: `OpportunityNoteAdded`
- **Trigger**: `OpportunityService.add_note`.
- **Payload**: `opportunity_id`, `note_id`.
- **Fires when**: the user saves a follow-up note on the opportunity.
- **Consumers**: none yet.

### `opportunity.note.deleted`

- **Event**: `OpportunityNoteDeleted`
- **Trigger**: `OpportunityService.delete_note`.
- **Payload**: `opportunity_id`, `note_id`.
- **Fires when**: the user removes a follow-up note.
- **Consumers**: none yet.

### `opportunity.link.added`

- **Event**: `OpportunityLinkAdded`
- **Trigger**: `OpportunityService.add_link`.
- **Payload**: `opportunity_id`, `link_id`.
- **Fires when**: the user attaches a titled source link (e.g. the LinkedIn post) to the opportunity. Link URLs must be http(s).
- **Consumers**: none yet.

### `opportunity.link.deleted`

- **Event**: `OpportunityLinkDeleted`
- **Trigger**: `OpportunityService.delete_link`.
- **Payload**: `opportunity_id`, `link_id`.
- **Fires when**: the user removes a source link.
- **Consumers**: none yet.

### `opportunity.moved_to_job`

- **Event**: `OpportunityMovedToJob`
- **Trigger**: `OpportunityService.move_to_job` links an existing job or creates one from the opportunity (manual "Move to Jobs" action).
- **Payload**: `opportunity_id`, `job_id`, `job_title`, `overall_score`, `recommendation`, `created_job`.
- **Fires when**: an evaluated opportunity is successfully linked to (or materialized as) a `job.jobs` row. Repeated moves are idempotent and fire nothing.
- **Consumers**: none yet (a future consumer could queue the new job for processing or notify dashboards).

## Emission Rules

- Events are emitted by the service that performs the state change — never by callers (rule 16b).
- Emission is best-effort and never changes business behavior (rule 16c).
- Tests assert emitted events through the collector (rule 16d).

# Related Documents

- `docs/domain/opportunities/opportunity.md`
