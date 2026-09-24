# Jobs Page

## Purpose

The Jobs page is the primary workspace for browsing, managing, and processing imported jobs.

Users can:

- Import new jobs
- Browse imported jobs
- Search jobs
- Filter jobs
- Sort jobs
- View job details
- Start AI Processing Execution
- Monitor live processing
- Open the Processing Queue
- Retry failed executions
- Review completed executions

The Jobs page always remains the primary workspace.

Background processing is completely separated from browsing and is monitored through the Processing Queue.

---

# Design Principles

The page follows these principles.

- Jobs are always the primary business entity.
- Browsing must never be blocked by background processing.
- Processing is asynchronous.
- The Job List is optimized for very large datasets.
- Users can continue working while jobs are processing.
- Live updates are received through Server-Sent Events (SSE).
- The Processing Queue is a monitoring tool, not a replacement for the Job List.

---

# High-Level Layout

```text
Jobs Page

├── Header
├── Toolbar
├── Job List
└── Processing Queue Drawer
```

---

# Desktop Layout

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Jobs                                                    Queue (2 Running • 4 Waiting)  ↻  + Add Job │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Search .................................................................................................... │
│                                                                                                              │
│ Sort ▼                                         Filters ▼                                   Refresh          │
├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                              │
│ # │ Job │ Company │ Location │ Scores │ Rec │ Processing │ Updated │
│──────────────────────────────────────────────────────────────────────────────────────────────────────────────│
│                                                                                                              │
│ 1 │ Senior Backend Engineer │ GetYourGuide │ Berlin │ [A+] #2 │ O 94 │ S 91 │ F 95 │ ★ Apply │ Ready │ 2m │
│ 2 │ Backend Engineer        │ Karla        │ Berlin │ [A+] #5 │ O 90 │ S 88 │ F 90 │ ☆ Apply │ Running │ now │
│ 3 │ Python Developer        │ Flexa        │ Remote │ [A] #9  │ O 83 │ S 84 │ F 86 │ — Skip │ Failed │ 5m │
│                                                                                                              │
│                                         Loading more jobs...                                                 │
│                                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

There is no fixed Actions column: hovering a row reveals a floating action
toolbar at the row's right edge (see # Row Actions).

---

# Primary Sections

## Header

Responsibilities

- Display page title.
- Display processing queue summary.
- Open Processing Queue drawer.
- Open Import Job dialog.
- Refresh the current result set.

Controls

| Control    | Description                                                                      |
| ---------- | -------------------------------------------------------------------------------- |
| Queue      | Opens the Processing Queue drawer.                                               |
| Add Job    | Opens the Import Job dialog. The button shows an `N` shortcut hint (`<kbd>N</kbd>`). |
| Refresh    | Reloads the current query (spins while a refetch is in flight).                  |

---

## Queue Badge

The Queue button always displays current execution statistics.

Example

```text
Queue

2 Running

4 Waiting
```

The badge is updated in real time through SSE.

---

## Toolbar

Responsibilities

- Search jobs.
- Filter jobs.
- Sort jobs.
- Refresh current result set.

Controls

| Control        | Description                              |
| -------------- | ---------------------------------------- |
| Search         | Search by title, company, keyword or job link (URL). |
| Status         | Filter by latest processing status.      |
| Location       | Filter by location (substring).          |
| Remote         | Filter by remote / on-site.              |
| Visa           | Filter by visa sponsorship.              |
| Pinned         | Toggle pinned-only view.                 |
| Recommendation | Multi-select filter by apply / consider / skip (OR). |
| Tracking       | Multi-select filter by application tracking status (OR). |
| Date           | Filter by created-at preset (Today / Yesterday / Last Week / Last Month). |
| Sort           | Sort current result set.                 |
| Columns        | Show / hide the Row number column. (Pinned state is managed from the Job Details Drawer.) |
| Clear          | Clears all active filters.               |
| Refresh        | Reload current query.                    |

Changing filters never reloads the entire page.

The current scroll position is preserved whenever possible.

---

# Job List

The Job List is implemented as a virtualized row-based table.

The frontend **does not use page numbers**.

Instead it uses **Infinite Loading**.

The backend still exposes a paginated API.

The frontend automatically requests the next page while the user scrolls.

The Job List preserves:

- Search
- Filters
- Sorting
- Scroll position

when opening Job Details.

---

# Infinite Loading

Loading sequence

```text
Open Jobs

↓

Load first page

↓

Render rows

↓

User scrolls

↓

Reach loading threshold

↓

Request next page

↓

Append rows

↓

Repeat until has_next = false
```

Configuration

| Property          | Value               |
| ----------------- | ------------------- |
| Initial page size | 50                  |
| Next page size    | 50                  |
| Load threshold    | 80% of visible list |
| Pagination        | Backend only        |
| Frontend UX       | Infinite Loading    |

The user never interacts with page numbers.

The backend remains fully paginated.

Benefits

- Continuous browsing.
- Smaller network requests.
- Excellent performance.
- Preserved scroll position.
- Scales to tens of thousands of jobs.

---

# Job Selection

Selecting a row opens the Job Details drawer.

The row never expands inline.

Opening Job Details never interrupts active processing.

The Processing Queue drawer may remain open independently.

---

# Data Refresh

The list is refreshed through two mechanisms.

## Manual Refresh

The Refresh button in the Header reloads the current query. It calls the same
`refetch` used by the error-state Retry button, so it works from any state
(including the error state, where the header remains available). While a
refetch is in flight the button is disabled and its icon spins.

## Keyboard Shortcut — Add Job

Pressing `N` anywhere on the Jobs page (unless the focus is inside an input,
textarea, select, or content-editable element) opens the Add Job drawer. This
is a jobs-only shortcut; there is no equivalent on the Companies or Skills
pages. The hint is shown on the Add Job button and its tooltip.

## Paste Shortcut — Add Job

Pressing **Ctrl+V / Cmd+V** anywhere on the Jobs page with a copied
`http(s)` link (and no editable element focused) opens the Add Job drawer
pre-filled with that URL. The URL is taken directly from the `paste` event,
so no clipboard permission is involved; non-URL clipboard content and pastes
inside inputs are left to the browser's native behavior. Like `N`, this is a
jobs-only shortcut. See `flows/jobs/paste-to-add-job.md`.

## Automatic Refresh

Live SSE updates mutate the affected row in place (status, timestamps,
scores) without re-rendering the whole table.

When an execution reaches a **terminal state** (completed / failed /
cancelled), the list query is also invalidated and refetched in the
background. This guarantees the row reflects what is actually persisted by
the pipeline — e.g. the job title extracted during analysis and the final
execution status — even across a reload. Non-terminal events update the row
in place only.

# Job Row

Each row represents a single Job.

The row provides a compact overview of:

- Job identity
- Company
- Location
- AI evaluation
- Processing state
- Last update
- Available actions

Rows are never expandable.

Selecting a row opens the Job Details Drawer.

---

# Row Columns

| Column         | Description                                         |
| -------------- | --------------------------------------------------- |
| #              | Row number within the loaded result set (toggleable) |
| Job            | Job title and employment type                       |
| Company        | Company logo and company name                       |
| Location       | City, country or Remote                             |
| Overall        | Overall AI Score                                    |
| Fit            | Fit Score                                           |
| Success        | Success Score                                       |
| Rank           | Position in the full list sorted by overall, then success, then fit (competition ranking: equal scores share a rank); display-only, absolute, independent of the current sort |
| Rec            | Apply / Consider / Skip badge                       |
| Tags           | User-defined labels + dismissed/visa/easy_apply badges (up to 2 visible lines, truncated with expand icon) |
| Tracking       | Application tracking status                         |
| Processing     | Current Processing Execution state                  |
| Updated        | Relative update time                                |

There is no `Actions` column — row actions are revealed on hover (see
`# Row Actions` below). The Row number column is hidden by default and can be
toggled via the toolbar Columns dropdown. Pinned state is managed from the Job
Details Drawer header, not from the row.

Rows support **dynamic height**: when a cell's content (especially Tags) exceeds
one line, the row grows to fit up to two lines. Content exceeding two lines is
truncated with `...` and a downward caret icon. The caret is visual only — the
full content is available via browser title tooltip on hover.

Rows highlight on hover (and while any inner control has focus) with a muted
background and an inset ring, so the focused row is always visually identifiable
in a long list.

---

# Column Details

##

Displays the legacy numeric identifier.

Example

```text
42
```

This value exists only for compatibility.

All new APIs use the UUID v7 identifier.

---

## Job

Displays

- Job title
- Employment type

Example

```text
Senior Backend Engineer

Full-time
```

---

## Company

Displays

- Company logo
- Company name

Example

```text
◉ GetYourGuide
```

If no logo exists

```text
□ GetYourGuide
```

---

## Location

Displays

Examples

```text
Berlin

Germany
```

or

```text
Remote
```

---

## Pin

The row itself has **no** pin button. Pinned state is shown and toggled from
the **Job Details Drawer** header (see `# Job Details Drawer`). The drawer
header pushpin is optimistic and does not reload the list. Activating the
Pinned filter in the toolbar shows only pinned jobs.

---

## Recommendation

Displays the analysis recommendation as a compact badge.

```text
Apply
Consider
Skip
```

Color and meaning

| Badge     | Meaning   | Color   |
| --------- | --------- | ------- |
| Apply     | Overall ≥ 80 | Emerald |
| Consider  | Overall ≥ 60 | Amber   |
| Skip      | Otherwise    | Gray    |

Jobs without a completed analysis show an em dash (`—`).

The column is display-only (no sort). Filtering by recommendation happens
through the toolbar's Recommendation filter.

---

# Overall Score

The Overall Score is the primary recommendation score.

It is calculated independently.

It is **not** the average of Fit and Success.

Example

```text
A++

94

Excellent Match
```

Color

| Grade | Color  |
| ----- | ------ |
| A++   | Green  |
| A+    | Green  |
| A     | Lime   |
| B     | Blue   |
| C     | Orange |
| D     | Red    |

Hovering displays

```text
Overall Score

Calculated using

• Shared Rules

• Job Rules

• AI Recommendation Rules
```

---

# Fit Score

Measures technical compatibility.

Example

```text
95
```

Hover

```text
Fit Score

Python Backend

DDD

FastAPI

PostgreSQL
```

---

# Success Score

Measures application success probability.

Example

```text
91
```

Hover

```text
Success Score

Visa

Relocation

Language

Market

Company
```

---

# Processing Column

The Processing column represents the current Processing Execution. For
dismissed jobs, this column shows a red "Dismissed" badge instead.

Examples

## Dismissed

```text
Dismissed
```

Red badge: `bg-red-500/10 text-red-500 border-red-500/20`.

---

## Ready

```text
Ready
```

---

## Queued

```text
Queued

Position #3
```

---

## Starting

```text
Starting...
```

---

## Running

```text
Extracting Resources

43%

2m remaining
```

---

## Completed

```text
Completed

5 minutes ago
```

---

## Failed

```text
Failed

Retry available
```

---

## Cancelled

```text
Cancelled
```

The Processing column updates live using SSE.

Only the affected row is updated.

The table must never refresh completely.

---

# Updated Column

Displays relative time.

Examples

```text
Just now

2 minutes ago

Yesterday
```

Hover shows the absolute timestamp, converted to the browser's **local** time.

```text
Jul 30, 2026, 4:32 PM (your local time)
```

The backend stores and serializes datetimes in UTC without a timezone marker;
the shared `DateTime` component interprets them as UTC and renders them in the
user's local timezone, so the displayed value always matches the current local
clock.

---

# Row Actions

There is no fixed Actions column. Hovering a row reveals a floating toolbar of
icon buttons at the row's right edge (using a `group`/`group-hover` pattern),
overlaid on the row so the freed column width is given to the data columns. The
toolbar's contents are context-sensitive to the processing status.

Each row contains two processing systems.

The Legacy system remains available.

The new AI Processing Execution is introduced alongside it.

| Action         | Description                               |
| -------------- | ----------------------------------------- |
| Legacy Process | Existing processing pipeline (deprecated) |
| AI Process     | Starts Processing Execution               |
| Retry          | Retry failed execution                    |
| Cancel         | Cancel queued execution                   |
| Details        | Open Job Details                          |
| More           | Additional actions                        |

---

# AI Process Button

The new button starts the Processing Execution workflow.

It is independent of the legacy implementation.

Clicking the button

```text
Ready

↓

Queued

↓

Processing Queue
```

The Jobs page remains visible.

The Queue drawer updates automatically.

---

# Processing Failure Banner

When a job's latest Processing Execution fails (e.g. it exceeds the
`WORKER_JOB_TIMEOUT` of 600s and `reconcile_stuck_executions` marks it failed),
the Job Details drawer shows a prominent, gracefully fading error banner at the
top of the content — instead of only a bare red line inside the collapsed
Processing section. The error fades in (`animate-in fade-in-0`) so it does not
pop abruptly, and offers two actions:

- **Retry** — re-runs processing for the job (when an `onReprocess` handler is
  wired into the drawer).
- **Check status** — refetches the job detail (and any new execution state) via
  the jobs detail API / SSE.

The backend fails a RUNNING execution once it exceeds `WORKER_JOB_TIMEOUT`
(default 600s) since `started_at`, showing a plain timeout message.

```text
┌──────────────────────────────────────────────────────────┐
│ ⨯ Processing failed                                      │
│ Execution timed out after 600s (worker stopped           │
│ responding).                                             │
│                                                          │
│ [ ↻ Retry ]   [ ⟳ Check status ]                         │
└──────────────────────────────────────────────────────────┘
   (red-tinted card, fades in; Retry hidden if no handler)
```

The same failure message also remains visible inside the collapsed **Processing**
section (with the fade-in), so it is not lost if the banner is dismissed.

---

# Legacy Process Button

The previous implementation remains available.

It is marked as

```text
Legacy
```

or

```text
Deprecated
```

No new features are added to the legacy workflow.

It exists only for migration compatibility.

# Processing Queue Drawer

The Processing Queue is a monitoring workspace.

It is **not** the primary place for managing jobs.

Users continue browsing the Job List while monitoring active executions.

The drawer slides in from the right.

It never replaces the Jobs page.

---

# Drawer Layout

```text
┌──────────────────────────────────────────────┐
│ Processing Queue                             │
│                                              │
│ Running (2)                                  │
│──────────────────────────────────────────────│
│ Senior Backend Engineer                      │
│ Extracting Resources                         │
│ ████████████░░░░░░░░░░ 43%                   │
│                                              │
│ Python Developer                             │
│ Scoring Job                                  │
│ ██████████████████░░░░ 71%                   │
│                                              │
│──────────────────────────────────────────────│
│ Waiting (4)                                  │
│──────────────────────────────────────────────│
│ Backend Engineer                             │
│ Position #1                                  │
│                                              │
│ DevOps Engineer                              │
│ Position #2                                  │
│                                              │
│──────────────────────────────────────────────│
│ Failed (1)                                   │
│──────────────────────────────────────────────│
│ Rust Engineer                                │
│ Retry                                        │
└──────────────────────────────────────────────┘
```

---

# Drawer Sections

The drawer always contains three sections.

## Running

Contains executions currently processed by workers.

Each execution displays

- Job title
- Current workflow step
- Progress bar
- Percentage
- Estimated remaining time

---

## Waiting

Contains queued executions.

Each execution displays

- Job title
- Queue position

Example

```text
Queued

Position #4
```

---

## Failed

Contains failed executions.

Each execution displays

- Job title
- Failure state
- Retry action

---

# Running Item

Example

```text
Senior Backend Engineer

Extracting Resources

██████████░░░░░░░░░░

43%

Estimated

2m remaining
```

---

# Workflow Progress

The drawer reflects the Processing Execution workflow.

Typical execution

```text
Queued

↓

Starting

↓

Initializing Context

↓

Loading Rules

↓

Loading Prompt

↓

Extracting Resources

↓

Extracting Job

↓

Scoring Job

↓

Generating Summary

↓

Persisting Results

↓

Completed
```

Each transition is streamed immediately through SSE.

---

# Live Updates

The drawer is completely event-driven.

Every Processing Execution publishes events.

Examples

```text
Queued

↓

Running

↓

Extracting Resources

↓

Scoring

↓

Completed
```

Only the affected execution is updated.

The drawer never refreshes completely.

---

# Server-Sent Events

The frontend subscribes once.

```text
GET

/api/sse/processing
```

The connection remains open.

Incoming events update

- Running list
- Waiting list
- Failed list
- Progress bars
- Current workflow stage
- Queue positions

No polling is used.

---

# Job Details Integration

Clicking an execution inside the drawer opens the Job Details drawer.

Opening `/jobs?job=<id>` opens the Job Details drawer for that job on mount
(e.g. from the company detail drawer's linked-jobs list).

The Processing Queue drawer automatically closes.

The user always has only one drawer open.

## Job Details Drawer layout

The Job Details drawer (shared `Drawer`, default `lg`, placement `right`)
shows a single scrollable page:

```text
┌─ Job Details ─────────────────────── [●] Application  ↻  ✎  ✕ ┐
│ [GradeBadge]  Overall: 78   Success: 74   Fit: 82  #3  [Why]│ ← score strip
│                                                         │
│ Software Engineer (Senior)                              │
│ Company  Acme GmbH →▾      │  Employment  Permanent   │
│ Location Berlin, DE…        │  Salary      €90k–€110k  │
│ Work Types Full-time, Remote│  Visa        EU Blue Ca… │
│ Apply     [Easy Apply]      │  hover/click → full      │
│ 🔗 Open job posting                                     │
│                                                         │
│ ┌─ Recommendation ─────────────────────────────┐        │
│ │ [Apply]  analyzed 2h ago                     │        │
│ │ Strong match for your visa profile...        │        │
│ └──────────────────────────────────────────────┘        │
│                                                         │
│ ┌─ Tagged Skills ──────────────────────────────┐        │
│ │ [TypeScript] [React] [Kubernetes] ...        │        │
│ └──────────────────────────────────────────────┘        │
│                                                         │
│ ┌─ Analysis (Summary / ...)┐                             │
│ └──────────────────────────┘                            │
│                                                         │
│ ┌─ Description ────────────────────────────────┐        │
│ └──────────────────────────────────────────────┘        │
│                                                         │
│ ▸ Published by — RecruitCo, TalentBridge GmbH           │
│                                                         │
│ ▸ Processing                                           │
└─────────────────────────────────────────────────────────┘
```

- **Score strip**: a `GradeBadge` for the overall grade plus colored
  Overall / Success / Fit score cards at the top. Colors use the shared
  `scoreColor` thresholds (≥90 green, ≥70 emerald, ≥50 yellow, ≥30 orange,
  <30 red) — identical to the list `ScoreBadge` colors. A `[#N]` **Rank**
  indicator after the Fit card shows the job's competition rank in the full
  job list sorted by overall, then success, then fit score (each descending,
  NULLS LAST) — jobs with identical scores share a rank. A `[Why]` button sits
  after the Overall score and
  opens a **Scores Explanation** popover anchored to the button. It
  auto-opens on hover and auto-closes on unhover; clicking the button pins
  the popover open and clicking again closes it. The popover lists *Why it
  fits*, *Chance of success* and *Concerns* — the same content that used to
  be an inline `Scores Explanation` section.
- **Header actions**: a pushpin **Pin** toggle (managed as described in
  `features/jobs/pinned-job.md`), `[Application]` opens the application
  workspace, a `↻ Reprocess` ghost button re-queues the job (same
  `onProcessV2` flow as the row's Reprocess action — the Queue drawer opens
  and the execution list refreshes), and `✎ Edit` opens the edit drawer.
  Reprocess renders only when a reprocess handler is provided.
- **Recommendation** is highlighted with `border-primary/20 bg-primary/5`
  (matching the Company Detail).
- **Published by** sits just before **Processing** at the end of the drawer
  as a `Collapsible` **collapsed by default**; the folded trigger shows the
  recruiter company names inline. Expanding reveals each recruiter link,
  its company-type badge and any extraction reasons.
- **Processing** sits at the end of the drawer inside a `Collapsible` that
  is **collapsed by default**; the caret reveals execution id, status,
  current step, any error, and the workflow steps.
- **Tagged Skills** render as compact badges (`[Skill · Ln · Category]`).
  Below the title a balanced two-column block (each half the drawer width)
  shows labeled rows: left `Company` (picker), `Location`, `Work Types`,
  `Apply` (Easy Apply badge when applicable); right `Employment`, `Salary`,
  `Visa`. Rows are aligned one-to-one across the columns. Both `Location`
  and `Visa` are truncated at 30 characters with an ellipsis; hovering
  reveals the full value in a tooltip, and clicking expands/collapses the
  value inline.

## Job Details — Set Company

The **Details** section has a `Company` row with a picker (`Change company`
button). It links the job to a company via `PUT /api/jobs/{id}/company`:

- **Link** — search companies and pick one; the job's `company_id` is set and
  its display name becomes the company's canonical name.
- **Unlink** — clears `company_id` (the stored company name is left as-is).

The picker is a searchable popover backed by `GET /api/companies/list`.

```text
Company  Acme GmbH →▾            (linked — name is a link, ▾ reopens the picker)

Company  Set company ▾           (not linked)
```

Once linked, the company name renders as a **deep link** to that company's
detail drawer on the Companies page (`/companies?company=<id>`); the caret
button next to it still reopens the picker to change or unlink the company.
When no company is linked, the row shows a `Set company` picker button.

## Job Details — Published by

When the job analysis extracted one or more **recruiter / staffing / agency**
companies (`related_companies` with `role="recruiter"` from the `job_companies`
table), a **"Published by"** section appears at the end of the drawer, just
before the Processing section:

```text
▸ Published by — RecruitCo, TalentBridge GmbH

   (expanded)
▾ Published by — RecruitCo, TalentBridge GmbH
  RecruitCo                                [recruiting
                                           agency]
  TalentBridge GmbH
  • listed as the recruiting partner
```

The section is a `Collapsible` **collapsed by default** — the folded trigger
shows the recruiter company names inline next to the caret. Expanding reveals
each recruiter row: a link to that company's detail drawer on the Companies
page (`/companies?company=<id>`) with an optional company-type badge. When any
recruiter carries an extraction `reason`, the reasons are listed beneath the
rows. The section is hidden when there are no recruiter companies.

The hiring company is always the `Company` row in Details (set by analysis or
manually via the picker) and is not duplicated in this section.

---

# User Flows

## Start Processing

```text
Click

AI Process

↓

Job

Queued

↓

Appears

Waiting

↓

Worker Available

↓

Running

↓

Completed
```

---

## Failure

```text
Running

↓

Error

↓

Failed

↓

Retry

↓

Queued
```

---

## Cancel

```text
Queued

↓

Cancel

↓

Cancelled

↓

Removed

from Queue
```

Running executions cannot be cancelled immediately.

They request graceful termination.

---

# Empty States

## Running Empty

```text
No jobs are currently processing.
```

---

## Waiting Empty

```text
Queue is empty.
```

---

## Failed Empty

```text
No failed executions.
```

---

# Connection States

## Connected

```text
Live Updates

Connected
```

---

## Reconnecting

```text
Reconnecting...

Attempt 2
```

---

## Disconnected

```text
Connection Lost

Retrying...
```

The frontend automatically reconnects using EventSource.

---

# Performance Rules

The Processing Queue must

- Update only modified executions.
- Never reload the complete drawer.
- Never reload the Job List.
- Support hundreds of simultaneous executions.
- Preserve scroll position during updates.
- Batch frequent UI updates when necessary.

---

# Accessibility

- Progress bars expose ARIA progress values.
- Queue changes are announced to screen readers.
- Keyboard navigation is fully supported.
- Drawer can be closed with Escape.
- Focus returns to the Queue button after closing.

# Responsive Behavior

## Desktop

The Jobs page is optimized for widescreen development workstations.

Layout

- Full-width virtualized Job List.
- Right-side Processing Queue drawer.
- Persistent toolbar.
- Sticky table header.

The Job List always remains visible while the Processing Queue drawer is open.

---

## Tablet

The layout adapts to medium screens.

Changes

- Reduced column spacing.
- Company logo becomes optional.
- Processing drawer width is reduced.
- Secondary columns may collapse.

Priority order

1. Job
2. Company
3. Overall
4. Processing
5. Actions

---

## Mobile

The page switches to a mobile-friendly layout.

Changes

- Rows become stacked cards.
- Toolbar collapses.
- Filters open in a bottom Drawer (vaul, default `lg`).
- Processing Queue opens as a full-screen modal.
- Infinite scrolling remains enabled.

---

# Search Behavior

## Keyboard Shortcut — Focus Search

Pressing `F` anywhere on the Jobs page (unless the focus is inside an input,
textarea, select, or content-editable element) moves focus to the Search field
and selects any existing query, so typing immediately starts a new search. The
`F` keypress itself is never inserted into the field. The same shortcut applies
to the Companies and Skills search fields.

Search is incremental.

Typing updates the result set after a **300ms debounce delay** — the toolbar
uses the shared `DebouncedInput` primitive (see
`docs/ux/design-system/input.md`). The input reflects keystrokes immediately,
but the server request fires only once typing pauses. Clearing the search is
immediate and cancels any pending request.

Supported fields

- Job Title
- Company Name
- Keywords
- Location

Search preserves

- Sorting
- Filters
- Scroll position (when possible)

---

# Filtering

Supported filters

- Pinned (see `# Pinned Filter` below)
- Recommendation
- Processing Status
- Location
- Overall Score
- Company
- Country
- Employment Type
- Remote / Hybrid / On-site
- Date Imported
- Processing State

Filters are applied server-side.

## Pinned Filter

A pushpin toggle in the toolbar restricts the list to pinned jobs.

```text
○ All Jobs
pinned Pinned only
```

When active it counts as an active filter and is cleared by the toolbar's
Clear action alongside the others. Pinning or unpinning a job while the
filter is active refetches the list so rows update immediately.

## Tags Filter

A multi-select dropdown in the toolbar restricts the list to jobs that have
all selected tags (intersection logic).

```text
Tags (2)
  ☑ python
  ☑ remote
  ☐ java
```

The dropdown collects unique tags from loaded jobs. Selecting multiple tags
shows only jobs that contain every selected tag. When active it counts as an
active filter and is cleared by the toolbar's Clear action alongside the
others.

## Recommendation Filter

A multi-select popover in the toolbar restricts the list to jobs whose
analysis produced **any** of the selected recommendations (OR semantics).

```text
┌────────────────────────┐
│ Recommendation [2] ▾    │  bordered box + chevron; [n] = selection count
├────────────────────────┤
│ ▢ Apply                │
│ ▢ Consider             │
│ ▢ Skip                 │
│ Clear                  │  clears this filter
└────────────────────────┘
```
When nothing is selected the trigger shows only the label (`Recommendation ▾`).
The box mirrors the other toolbar filter boxes (bordered, down-chevron); once
selections exist it shows a small count badge (the number of selected values)
instead of the joined labels, keeping the toolbar compact.

Selecting one or more options sends `recommendation=apply&recommendation=skip`
(repeated query params) to the backend, which matches jobs whose analysis
recommendation is in the chosen set. Jobs without a completed analysis never
match. When active it counts as an active filter and is cleared by the
toolbar's Clear action alongside the others.

## Tracking Filter

A multi-select popover in the toolbar restricts the list to jobs whose
application tracking status is **any** of the selected statuses (OR semantics).
The full set of tracking statuses is available (the legacy single-select
dropdown omitted `Seen`, `Preparing` and `Ready to Apply`):

```text
┌────────────────────────┐
│ Tracking [3] ▾         │  bordered box + chevron; [n] = selection count
├────────────────────────┤
│ ▢ Not Applied          │
│ ▢ Seen                 │
│ ▢ Preparing            │
│ ▢ Ready to Apply       │
│ ▢ Applied              │
│ ▢ Interview            │
│ ▢ Offer                │
│ ▢ Accepted             │
│ ▢ Rejected             │
│ ▢ Withdrawn            │
│ ▢ Expired              │
│ Clear                  │  clears this filter
└────────────────────────┘
```
When nothing is selected the trigger shows only the label (`Tracking ▾`). The box
mirrors the other toolbar filter boxes (bordered, down-chevron); once selections
exist it shows a small count badge (the number of selected statuses) instead of
the joined labels, keeping the toolbar compact.

Selecting `Not Applied` together with specific statuses unions jobs that have
no application with jobs whose latest application status matches. The selected
values are sent as repeated `tracking_status=applied&tracking_status=interview`
query params (comma-separated values are also accepted). When active it counts
as an active filter and is cleared by the toolbar's Clear action alongside the
others.

## Processing Status Filter

The status filter lives in the toolbar and groups jobs by their **latest**
processing execution status:

```text
All
Created
Queued
Running
Completed
Failed
Not processed
```

`Not processed` selects jobs that have **no** processing execution at all —
jobs that were imported but never queued. Selecting it counts as an active
filter and is cleared by the toolbar's Clear action alongside the others.

---

# Location Filter

A compact input in the toolbar filters jobs by location.

Typing matches the job's location case-insensitively (substring match) — e.g.
`berlin` matches `Berlin, Germany`.

```text
Berlin, Germany
Amsterdam, Netherlands
Hamburg, Germany
```

The input is debounced (**300ms**, via `DebouncedInput`) so requests fire only
after typing pauses. An active location shows a ✕ clear button and counts as an
active filter, cleared by the toolbar's Clear action alongside the others.

---

# Sorting

Supported sort fields

- Imported Date
- Updated Date
- Overall Score
- Fit Score
- Success Score
- Company Name
- Job Title
- Status

Sorting is always performed by the backend.

Every sort follows a NULLS LAST policy: jobs where the sort column is empty
(for example a job that has not been scored yet) always sort last, in both
ascending and descending order.

Score sorts are multi-column so ties on the primary score are broken
deterministically, sharing the chosen ascending/descending direction:

- **Overall Score** → overall, then success, then fit
- **Fit Score** → fit, then overall, then success
- **Success Score** → success, then overall, then fit

The Status sort orders rows by the same status each row displays (the latest
processing execution). Jobs that were never processed always sort last, in both
ascending and descending order.

---

# Empty States

## No Jobs

```text
No jobs have been imported yet.

Import your first job to begin.
```

Actions

- Import Job

---

## Importing a Duplicate Job

When the submitted job post URL already exists, the Import Job drawer keeps the
entered notes unsaved and shows the conflict note with a link to the existing
job's **application** page:

```text
  ✕  A Job with the same primary URL already exists.   [Open application →]
```

- The link points to `/jobs/{job_id}/application` for the existing job.
- No new note is written to the job's notes; the provided note is not saved.

---

## No Search Results

```text
No matching jobs were found.

Try another keyword or remove filters.
```

---

## No Filter Results

```text
No jobs match the selected filters.
```

Action

```text
Clear Filters
```

---

# Loading States

## Initial Loading

Display

- Skeleton rows
- Loading indicator

The page layout must remain stable.

---

## Infinite Loading

When requesting the next page

```text
Loading more jobs...
```

Existing rows remain interactive.

---

## Refreshing

Refreshing does not clear the table.

Only affected rows are updated.

---

# Error States

## Backend Error

```text
Unable to load jobs.

Retry
```

---

## Network Error

```text
Connection lost.

Trying to reconnect...
```

---

## SSE Disconnected

```text
Live updates unavailable.

Reconnecting...
```

The user can continue browsing.

Only live updates pause temporarily.

---

# Row Density

Supported display modes

## Comfortable

Row Height

```text
80px
```

Default mode.

---

## Compact

Row Height

```text
64px
```

Optimized for large datasets.

---

# Accessibility

The page follows WCAG AA.

Requirements

- Keyboard navigation.
- Screen-reader labels.
- ARIA progress indicators.
- Visible focus states.
- High contrast support.
- Reduced motion support.

Keyboard shortcuts

| Shortcut | Action           |
| -------- | ---------------- |
| ↑ ↓      | Navigate rows    |
| Enter    | Open Job Details |
| Esc      | Close Drawer     |
| F        | Focus Search     |
| N        | Open Add Job drawer |

---

# Performance Requirements

The page must support

- 100,000+ jobs
- Virtual scrolling
- Infinite loading
- Partial row updates
- Stable scroll position

The frontend must never render all rows simultaneously.

Only visible rows are mounted.

---

# Design Tokens

## Status Colors

| Status    | Color  |
| --------- | ------ |
| Ready     | Gray   |
| Queued    | Blue   |
| Running   | Cyan   |
| Completed | Green  |
| Failed    | Red    |
| Cancelled | Orange |

---

## Score Colors

| Grade | Color  |
| ----- | ------ |
| A++   | Green  |
| A+    | Green  |
| A     | Lime   |
| B     | Blue   |
| C     | Orange |
| D     | Red    |

---

# Icons (Lucide)

| Element        | Icon              |
| -------------- | ----------------- |
| Import Job     | Plus              |
| Pin            | Pushpin           |
| Queue          | Workflow          |
| Search         | Search            |
| Filters        | SlidersHorizontal |
| Refresh        | RefreshCcw        |
| Legacy Process | PlayCircle        |
| AI Process     | Sparkles          |
| Retry          | RotateCcw         |
| Cancel         | Square            |
| Details        | Eye               |
| More           | EllipsisVertical  |
| Completed      | CircleCheck       |
| Failed         | CircleX           |
| Running        | LoaderCircle      |
| Waiting        | Clock3            |

---

# Related Documents

- `docs/workflows/job-processing.md`
- `docs/domain/processing/processing-execution.md`
- `docs/domain/processing/events.md`
- `docs/api/jobs/list-jobs.md`
- `docs/api/processing/process-job.md`
- `docs/api/sse/processing-events.md`
- `docs/ux/features/jobs/job-row.md`
- `docs/ux/features/jobs/processing-queue.md`
- `docs/ux/flows/jobs/browse-jobs.md`
- `docs/ux/flows/jobs/process-job-live.md`
- `docs/domain/processing/job-state-machine.md`
