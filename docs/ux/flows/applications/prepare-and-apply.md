# Prepare and Apply Flow

## Purpose

This flow defines the user journey from a Job to an **application** in the Job
Application Workspace (`/jobs/{job_id}/application`): creating the application record,
tracking its status and follow-ups, and applying.

It does not define the AI generation journey (see
`generate-application-artifacts.md`).

## Actors and Entry Points

A user can enter the workspace from either:

- A **job row action** (airplane icon, tooltip "Application") on the Jobs page, or
- The **Application** button in the **Job Detail drawer** header.

## Overview

```text
Job row / Job detail drawer
        │  click Application
        ▼
Workspace at /jobs/{id}/application
        │
        ├── no application?  ──▶  [Create Application] ──▶ status "recommended"
        │
        ▼
  APPLICATION  tracker section
        │  set status (records a timeline node), follow-ups
        ▼
  PREPARATION / DOCUMENTS      (see generate-application-artifacts.md)
        │
        ▼
  status → "applied" (timeline records the applied date)  ← follow-ups scheduled
```

## Flow Steps

1. **Enter the workspace** from a job row action or the drawer button.
2. **Create the application** (if none exists): the workspace shows the empty state with
   `[Create Application]`. `POST /api/applications {job_id}` creates the record with
   status `recommended` (201) and the three sections appear.
3. **Track the pipeline**: the tracker section shows status and its timeline.
   - The user moves status through `recommended → preparing → ready_to_apply → applied`
      (or `rejected` / `withdrawn` / `expired`). Each change appends a timeline node with the time set
     to *now* (editable in the timeline box).
4. **Schedule follow-ups**: add a note + optional date; toggle ☐/☑ as actions happen.
5. **Generate the roadmap and documents** (see the generation flow), then mark the
   application **Applied** — the timeline records the applied date.

## State Diagram

```mermaid
stateDiagram-v2
    [*] --> NoApplication
    NoApplication --> Recommended: Create Application
    Recommended --> Preparing: status change
    Preparing --> ReadyToApply: status change
    ReadyToApply --> Applied: status change
    Applied --> Rejected: status change
    Applied --> Withdrawn: status change
    Applied --> Applied: add/complete follow-ups
    Rejected --> [*]
    Withdrawn --> [*]
```

## Sequence

```mermaid
sequenceDiagram
    actor U as User
    participant W as Workspace
    participant API as /api/applications
    U->>W: click Application (row / drawer)
    W->>API: GET /by-job/{job_id}
    alt no application
        API-->>W: 404
        W-->>U: empty state + [Create Application]
        U->>W: click Create Application
        W->>API: POST {job_id}
        API-->>W: 201 {status: "recommended"}
    else application exists
        API-->>W: 200 detail (status_timeline, follow_ups, documents) + GET /api/roadmaps/by-application
    end
    U->>W: set status
    W->>API: PATCH /applications/{id}
    U->>W: add follow-up
    W->>API: POST /{id}/follow-ups
    API-->>W: 201 follow-up (tracker refreshes)
```

## Edge Cases

- **Application already created** (repeat entry from another browser): creating again
  surfaces a conflict — the UI shows an error toast.
- **Job deleted**: `GET /by-job` returns 404 and the workspace shows "Unable to load the
  job."; the "Back to Job" link still works.
- **Follow-up with no note and no date**: the Add button is disabled.

# Related Documents

- `docs/ux/features/applications/workspace.md`
- `docs/ux/features/applications/application-tracker.md`
- `docs/ux/flows/applications/generate-application-artifacts.md`
