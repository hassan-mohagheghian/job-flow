# Workflow Progress Component

## Purpose

The Workflow Progress component displays the current execution progress of a Job workflow.

It provides users with:

- Current processing stage.
- Completed steps.
- Running steps.
- Failed steps.
- Nested workflow details.
- Progress visibility.

The component is used inside:

- Processing Queue Drawer.
- Job Details page.
- Future execution history views.

---

# Responsibility

Workflow Progress is responsible for displaying workflow state.

It does not:

- Execute workflows.
- Manage execution state.
- Communicate directly with LangGraph.
- Manage SSE connections.

The component only consumes WorkflowProgress data.

---

# Data Source

Input model:

WorkflowProgress

Provided by:

- ProcessingExecution API.
- SSE processing events.

Related documents:

- docs/domain/processing/workflow-progress.md
- docs/api/processing/get-processing-execution.md
- docs/api/sse/processing-events.md

---

# Component Structure

WorkflowProgress

    WorkflowStepList

        WorkflowStep

            WorkflowStepChildren

---

# UI Concept

The default view should show high-level workflow steps.

Users should be able to expand steps to see details.

The UI should balance:

- Visibility.
- Simplicity.
- Debugging capability.

---

# UI Mock: Workflow Progress Tree

Place:

This is the main workflow visualization.

Example:

    Workflow Progress

    Load Job

    ✓ Load Job
      Completed

    ✓ Collect Sources
      Completed

    ⟳ Fetch Content
      Progress: 60%

        ✓ Primary Job URL
          Completed

        ⟳ Company Website
          Running
          Progress: 40%

        ○ Additional Links
          Pending

    ○ Extract Content
      Pending

    ○ Build Context
      Pending

    ○ Validate Context
      Pending

    ○ Save Context
      Pending

    ○ Analyze Job
      Pending

    ○ Extract Skills
      Pending

    ○ Score Job
      Pending

    ○ Recommendation
      Pending

    ○ Summarize
      Pending

    ○ Save Results
      Pending

The combined workflow exposes 13 user-facing steps. Internal nodes
(`execution_failed`, `context_ready`, `analysis_ready`, `load_context`,
`prepare_profile`) are never rendered.

---

# Step Display

Each workflow step displays:

- Status icon.
- Step title.
- Progress percentage.
- Optional child steps.
- Optional error information.

Example:

Running step:

Fetch Content

Status:

Running

Progress:

60%

Completed step:

✓ Fetch Content

Status:

Completed

Failed step:

! Fetch Content

Status:

Failed

Pending step:

○ Fetch Content

Status:

Pending

---

# Step States

Supported states:

- pending
- running
- completed
- failed
- skipped

---

# Status Representation

## Pending

Meaning:

The step has not started yet.

Display:

○

---

## Running

Meaning:

The step is currently executing.

Display:

⟳

Optional:

Progress percentage.

Example:

Fetch Content

Running

60%

---

## Completed

Meaning:

The step finished successfully.

Display:

✓

Example:

✓ Fetch Content

Completed

---

## Failed

Meaning:

The step failed.

Display:

!

The UI may display:

- Error message.
- Retry action.

Example:

! Fetch Content

Failed

Reason:

Primary URL timeout

---

## Skipped

Meaning:

The step was intentionally skipped.

Display:

—

---

# Nested Steps

Steps may contain children.

Example:

Parent step:

Fetch Content

Children:

- Primary URL.
- Company Website.
- Additional Links.

Rules:

- Children are hidden by default.
- Users expand when needed.
- Parent progress is calculated by backend.
- Frontend only renders the received state.

---

# Expand / Collapse Behavior

Default:

Collapsed.

Collapsed state:

    Fetch Content

    Progress: 60%

Expanded state:

    Fetch Content

    Progress: 60%

        ✓ Primary URL

        ⟳ Company Website

        ○ Additional Links

---

# UI Mock: Step Expansion States

Collapsed:

    +--------------------------------+
    | ⟳ Fetch Content          60%   |
    +--------------------------------+

Expanded:

    +--------------------------------+
    | ⟳ Fetch Content          60%   |
    +--------------------------------+
    |                                |
    |   ✓ Primary URL                |
    |     Completed                  |
    |                                |
    |   ⟳ Company Website            |
    |     Running 40%                |
    |                                |
    |   ○ Additional Links            |
    |     Pending                    |
    |                                |
    +--------------------------------+

---

# Progress Calculation

The component does not calculate progress.

Backend provides:

- Step progress.
- Workflow progress.

Frontend responsibility:

- Render progress.
- Render state.
- Render transitions.

---

# Animation Rules

Allowed:

- Progress bar animation.
- Step status transition.
- Expand/collapse animation.

Avoid:

- Continuous movement.
- Excessive animations.
- Automatic expansion of steps.

---

# Error Display

Failed steps may show error details.

Example:

Fetch Content

Status:

Failed

Reason:

Primary URL timeout

Error details should be expandable.

Errors are prefixed with the failing step, e.g. `[load_job]`:

Reason:

`[load_job] Failed to parse job data: ...`

---

# Responsive Behavior

Desktop:

Display full workflow tree.

Mobile:

Display collapsed step list.

Users expand individual steps when needed.

---

# Accessibility

Requirements:

- Keyboard expandable steps.
- Screen reader labels.
- Status should not rely only on color.
- Progress values must have accessible labels.

---

# Empty State

If workflow has no steps:

Display:

No workflow progress available.

---

# Loading State

While loading:

Display:

Workflow Progress

Loading steps...

---

# Integration With Processing Queue

Processing Queue owns:

- Execution item.
- Job status.
- Actions.

Workflow Progress owns:

- Step visualization.
- Progress display.
- Step expansion.

---

# Design Rules

- Show high-level workflow steps by default.
- Hide detailed child steps initially.
- Allow manual expansion.
- Do not expose internal LangGraph nodes.
- Do not expose worker implementation details.
- Do not connect directly to SSE.
- Consume state from parent components.

---

# Job Details Drawer — AI Analysis

Once a job finishes processing, the Job Details Drawer (xl, right side) shows
an "AI Analysis" section fed by `GET /api/jobs/{job_id}` → `analysis`. It is
refetched live when the execution completes/fails (SSE invalidates the
`['job-detail', jobId]` query).

```text
┌──────────────────────────────────────────────────────────────┐
│ Senior Backend Engineer                                      │
│ GetYourGuide · Berlin                                        │
├──────────────────────────────────────────────────────────────┤
│ [A+]  Overall 91   Fit 94   Success 88                      │
│                                                              │
│ Recommendation                      [ Apply ]                │
│  Because the role matches your Go + Postgres stack and the   │
│  company invests in its engineering team.                    │
│                                                              │
│ AI Analysis                    generated Jul 30, 2026, 4:32 PM │
│                                                              │
│  Why it fits                                                  │
│    • Go, PostgreSQL, Kubernetes — core stack match           │
│    • 4+ yrs seniority required, you have 5                   │
│  Likelihood of success                                        │
│    • Strong referral network in Berlin                        │
│    • Competitive salary range (85-95k)                       │
│  Concerns                                                     │
│    • No Kafka experience (required, low)                     │
│                                                              │
│  Summary                                                      │
│    Senior backend role at GetYourGuide, Berlin. Good fit,    │
│    apply with Kafka spike on the resume.                     │
│    Resume fit: Strong                                       │
│    Note: Emphasize distributed-systems work.                 │
│                                                              │
│  Skills                                                       │
│    • Go           Language   ████ 4  matched  “required”     │
│    • PostgreSQL   Database   ████ 4  matched  “daily use”    │
│    • Kubernetes   Infra      ███  3  matched  “k8s stack”    │
│    • Kafka        Data       █    1  low      “eventing”     │
│    • Vue.js       Frontend   —      missing  “modern UI”     │
│                                                              │
│  Insights                                                     │
│    • Highlight distributed-systems projects in the cover     │
│    • Salary is negotiable — apply early                      │
└──────────────────────────────────────────────────────────────┘
```

The Recommendation section (recommendation badge + apply reason) is
prioritized directly below the score grid at the top of the drawer; the AI
Analysis section then shows the generated timestamp, insights, score
explanations, summary and tagged skills. The grade badge (`[A+]`) is derived
from the overall score via the shared grade helper.

For legacy rows (processed before the analysis phase existed) the section
renders from the `jobs`/`summaries` projections without a recommendation
badge.

---

# Related Documents

- docs/ux/features/jobs/processing-queue.md
- docs/ux/flows/jobs/process-job-live.md
- docs/domain/processing/workflow-progress.md
- docs/api/processing/get-processing-execution.md
- docs/api/sse/processing-events.md
- docs/architecture/frontend-sync.md
