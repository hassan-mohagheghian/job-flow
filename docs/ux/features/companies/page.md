# Companies Page

## Purpose

The Companies page is the workspace for browsing and managing processed companies.

Users can:

- Add a new company (via notes and links)
- Browse processed companies
- Search companies
- Filter companies by industry
- Filter companies by processing status
- Pin companies for attention
- Sort companies
- View company details (intelligence, scores, notes, jobs)
- Manage related companies (set / remove a main company via the detail drawer)
- Edit company core data
- Reprocess a company
- Delete a company
- Open the shared Processing Drawer (filtered to companies)

The Companies page mirrors the Jobs v2 page UX: virtualized table, server-side
pagination, infinite scroll, and vaul-based drawers (shared `Drawer`).

---

# Design Principles

The page follows these principles.

- Companies are always the primary business entity.
- Browsing must never be blocked by background processing.
- Company processing runs through the shared `ProcessingExecution` / SSE model
  (same as Jobs) — a two-phase workflow (context preparation without LLM, then a
  single-LLM analysis). It is monitored through the shared Processing Drawer
  filtered to companies, fed by `GET /api/processing/queue` + SSE.
- The Company List is optimized for very large datasets.
- Users can continue working while companies are processing.

---

# High-Level Layout

```text
Companies Page

├── Header
├── Toolbar
├── Company List
├── Processing Drawer (companies filter)
├── Company Detail Drawer
├── Relate Company Dialog (from the detail drawer)
├── Company Edit Drawer
└── Add Company Drawer
```

---

# Desktop Layout

```text
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ ⛭ Companies (128)                    Loaded 25 of 128          Queue (3)   ↻  + Add Company │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│ Search .........................        [Industry ▾] [Type ▾] [Status ▾] [Pinned] [Columns] [Clear]│
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                               │
│ # │ Name │ Industry │ Type │ Location │ Size │ Jobs │ Scores │ Status │ Updated │ Created │
│──────────────────────────────────────────────────────────────────────────────────────────────────────────────────│
│ 1 │ Acme │ Software │ Product │ Berlin │ 1-50 │ 12   │ [A+] O 88 │ S 90 │ F 85 │ Completed │ 2m │ 2h │
│ 2 │ Beta │ Fintech  │ Consulting │ Munich │ 51-200│ 4    │ [B] F 60  │ S 55 │ O 58 │ Completed │ 5m │ 1d │
│ 3 │ Nova │ Health   │ —    │ —    │ 0    │ [—] F —   │ S —  │ O —  │ —         │ 1h │ 2d │
│                                                                                               │
│                                        Loading more companies...                              │
│                                                                                               │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# Primary Sections

## Header

Responsibilities

- Display page title and total count.
- Display loaded-vs-total count.
- Open the shared Processing Drawer (companies filter).
- Open Add Company drawer.
- Refresh the current result set.

Controls

| Control     | Description                                                       |
| ----------- | ----------------------------------------------------------------- |
| Queue       | Opens the shared Processing Drawer (companies).                   |
| Add Company | Opens the Add Company drawer.                                     |
| Refresh     | Reloads the current query (spins while a refetch is in flight).   |

---

## Queue Button

The Queue button opens the shared Processing Drawer filtered to
`target_type: company`.

```text
Queue
```

The drawer is fed by `GET /api/processing/queue` and live SSE
(`/events/processing`), showing Running / Waiting / Failed sections with
Start / Retry / Remove / Cancel actions. No polling is used.

---

## Toolbar

Responsibilities

- Search companies.
- Filter companies by industry.
- Filter companies by company type (product / recruiting / staffing / consulting).
- Filter companies by processing status.
- Filter companies by pinned state.
- Clear active filters.

Controls

| Control  | Description                                    |
| -------- | ---------------------------------------------- |
| Search   | Search by name, industry, city or description. |
| Industry | Filter by exact industry.                      |
| Type     | Filter by company type (Product, Recruiting agency, Staffing, Consulting, Unknown). |
| Status   | Filter by exact processing status.             |
| Pinned   | Toggle pinned-only view.                       |
| Columns  | Show / hide the Row number column. (Pinned state is managed from the Company Detail Drawer.) |
| Clear    | Clears all active filters.                     |

Changing filters never reloads the entire page.

Search is debounced (300ms) via the shared `DebouncedInput` primitive.

Pressing `F` anywhere on the page (unless the focus is inside an input,
textarea, select, or content-editable element) moves focus to the Search field
and selects any existing query, so typing immediately starts a new search. The
`F` keypress itself is never inserted into the field. The same shortcut applies
to the Jobs and Skills search fields.

---

# Company List

The Company List is implemented as a virtualized row-based table (mirrors the
Jobs v2 `JobsTable`).

The frontend **does not use page numbers**.

Instead it uses **Infinite Loading** via cursor-based pagination.

The backend exposes a cursor-paginated API (`GET /api/companies/list`).

The Company List preserves:

- Search
- Industry filter
- Status filter
- Sorting
- Scroll position

when opening Company Details.

---

# Infinite Loading

Loading sequence

```text
Open Companies

↓

Load first page (page_size=25)

↓

Render rows

↓

User scrolls

↓

Reach loading threshold (sentinel, 200px margin)

↓

Request next page with cursor

↓

Append rows

↓

Repeat until has_more = false
```

Configuration

| Property          | Value            |
| ----------------- | ---------------- |
| Initial page size | 25               |
| Next page size    | 25               |
| Pagination        | Backend only     |
| Frontend UX       | Infinite Loading |

---

# Row Columns

| Column   | Description                                            |
| -------- | ------------------------------------------------------ |
| #        | Row number within the loaded result set (toggleable)   |
| Name     | Company logo and name                                  |
| Industry | Industry classification                                |
| Type     | Company type badge (Product / Recruiting Agency / Staffing / Consulting / Unknown) |
| Location | City, Country                                          |
| Size     | Company size band                                      |
| Jobs     | Jobs count, adapted to role: hiring jobs for product companies, listed jobs for recruiters |
| Scores   | Grade badge + Overall / Success / Fit score values     |
| Status   | Processing status from the latest processing execution |
| Updated  | Relative update time                                   |
| Created  | Relative creation time                                 |

There is no `Actions` column — row actions are revealed on hover (see
`features/companies/company-row.md#actions`). The Row number column is hidden
by default and can be toggled via the toolbar Columns dropdown. Pinned state
is managed from the Company Detail Drawer header, not from the row.

Rows highlight on hover (and while any inner control has focus) with a muted
background and an inset ring, so the focused row is always visually identifiable
in a long list.

---

# Column Details

## Pin

The row itself has **no** pin button. Pinned state is shown and toggled from
the **Company Detail Drawer** header (see `features/companies/company-detail.md`).
The drawer header pushpin is optimistic — the pin updates immediately and is
rolled back on failure.

## Name

Displays

- Company logo (if present)
- Company name

```text
◉ Acme GmbH
```

---

## Industry

Displays the company industry, truncated.

```text
Software Development
```

---

## Type

Displays a compact badge with the formatted company type (Product Company,
Recruiting Agency, Staffing Company, Consulting Company, or Unknown). See
`features/companies/company-row.md#company-type-column`.

Rows are tinted by company type: **product companies stay white** (no tint),
while every other type gets its **own unique color** (Recruiting Agency =
purple, Staffing = orange, Consulting = teal, Unknown = muted). See
`features/companies/company-row.md#company-type-row-colors`.

---

## Location

Displays `City, Country`, or an em dash.

```text
Berlin, Germany
```

---

## Size

Displays the company size band.

```text
51-200
```

---

## Jobs

Shows the number of jobs the company is involved in, adapted to its role:

- **Product / other companies** — count of linked, non-deleted jobs where the
  company is the hiring employer (`JobModel.deleted == 0`, `job_count`).
- **Recruiter-type companies** (`RECRUITING_AGENCY` / `STAFFING_COMPANY`) —
  count of jobs the company **lists** for its clients (`recruiter_job_count`):
  recruiter jobs that have an attributed distinct hiring company.

```text
12                              ← product company (jobs it hires for)
7  (tooltip: "7 jobs listed     ← recruiter company (jobs it lists)
    for clients")
```

Zero jobs displays `—`.

---

## Scores

Displays the overall grade badge (derived from the overall score via the shared
grade helper, `A++` … `D`) followed by three compact score badges.

```text
[A+]  O 88   S 90   F 85
```

Color thresholds (matches `ScoreBadge` in jobs-v2):

| Value | Color   |
| ----- | ------- |
| ≥ 90  | Green   |
| ≥ 70  | Emerald |
| ≥ 50  | Yellow  |
| ≥ 30  | Orange  |
| < 30  | Red     |

Null scores display `—`.

---

## Status

Displays the processing status derived from the company's **latest processing
execution** — the exact source and shared `StatusBadge` the Jobs list uses
(`ExecutionStatus` vocabulary). Companies with no execution render `—`.

| Status    | Color                        |
| --------- | ---------------------------- |
| created   | Gray                         |
| queued    | Blue                         |
| starting  | Amber                        |
| running   | Green (pulsing dot)          |
| completed | Green                        |
| failed    | Red                          |
| cancelled | Gray                         |

---

## Updated

Displays relative time via the shared `DateTime` component.

```text
Just now

2 minutes ago
```

---

## Created

Displays relative creation time via the shared `DateTime` component.

```text
2 hours ago

2 days ago
```

---

# Row Actions

There is no fixed Actions column. Hovering a row reveals a floating toolbar of
four icon actions (tooltip buttons) at the row's right edge:

| Action    | Description                             |
| --------- | --------------------------------------- |
| Details   | Opens Company Details drawer.           |
| Reprocess | Re-enqueues the company for processing. |
| Edit      | Opens Company Edit drawer.              |
| Delete    | Deletes the company (with confirm).     |

All row actions stop propagation so clicking an action never opens the detail
drawer.

---

# Company Detail Drawer

Selecting a row opens the Company Detail drawer (shared `Drawer` from the right).

The drawer shows a single scrollable page (no tabs), mirroring the Job Detail
drawer:

- Overall grade badge (derived from the overall score) + Overall / Success / Fit
  score cards, then company name, logo, industry and meta badges
- Link column at the top-right of the score strip — Website first, then the
  remaining `company.links` beneath it (each opens in a new tab, skipping any
  link equal to the website) — mirrors the Job Detail drawer's "Open job
  posting" link
- Header actions: Reprocess (re-enqueues for processing) and Edit — ghost
  buttons at the top-right, beside the "Company Details" title
- Recommendation (prioritized to the top)
- Intelligence sections (product or recruiter variant)
- Scores explanation (Why popover next to the header score cards)
- Linked jobs list (`CompanyJobsTab`)
- Notes & Links — read only (CRUD lives in the Edit drawer)

There is no bottom action footer: the "View All Jobs" and "Delete" buttons
were removed. Deleting a company is done via the row actions; job navigation
happens per-row inside the Linked Jobs section.

The drawer loads the company once via `GET /api/companies/list/{id}`, which
returns all company data (base fields, status, notes, links, intelligence,
scores, jobs) in a single payload. The sections read from that payload — no
separate `/links`, `/jobs` or local-history calls are made.

---

# Company Edit Drawer

The Edit drawer (shared `Drawer`) edits core company fields plus notes and links:

- Name (required)
- Industry
- City / Country
- Company Size / Company Type
- Website
- Description
- Notes & Links — `CompanyNotesTab` (notes + links CRUD)

Saving calls `PUT /api/companies/{id}` and invalidates the list and detail
queries.

---

# Add Company Drawer

The Add Company drawer (shared `Drawer`) collects:

- Free-text notes (company name, description, observations)
- Links (LinkedIn, Website, Careers, GitHub, custom)

Submitting calls `POST /api/companies` with `{name, notes, links,
source: "web", queue}`. The company is created and, when queued, a
`COMPANY_PROCESSING` `ProcessingExecution` starts (the response includes
`execution_id`). After a successful submit the drawer closes and the company
appears in the list with its processing status.

---

# Processing Drawer (Companies)

The Processing Drawer is the **shared** `ProcessingDrawer`
(`shared/components/ProcessingDrawer.tsx`) opened with `targetType="company"`,
so it lists only company executions. It is the same drawer the Jobs page uses
with `targetType="job"`.

It is fed by `GET /api/processing/queue` and live SSE
(`/events/processing`, filtered by `target_type: "company"`). No polling is
used.

Sections:

| Section | Action        |
| ------- | ------------- |
| Running | Cancel        |
| Waiting | Start, Remove |
| Failed  | Retry, Remove |

Each item shows the company name, current step / status, links, and (in the
expanded view) the workflow step tree with progress.

Start / Cancel / Retry call `/api/processing/executions/{id}/...`; Remove calls
`DELETE /api/processing/queue/{execution_id}`.

> Company processing runs through the shared ProcessingExecution lifecycle —
> context preparation without LLM, then a single-LLM analysis — streaming
> per-step progress over SSE exactly like Jobs.

---

# Pinned Filter

A pushpin toggle in the toolbar restricts the list to pinned companies.

```text
○ All Companies
pinned Pinned only
```

When active it counts as an active filter and is cleared by the toolbar's Clear
action alongside the others. Pinning or unpinning a company while the filter is
active refetches the list so rows update immediately.

---

# Status Filter

A dropdown in the toolbar restricts the list to companies whose processing
status matches exactly (server-side filter on `GET /api/companies/list?status=`).

```text
Status ▾
├── All
├── Created
├── Queued
├── Running
├── Completed
├── Failed
└── Not processed
```

The status is derived from the company's **latest processing execution** (the
same source and vocabulary as the Jobs toolbar). `Not processed` selects
companies with no execution at all. When active it counts as an active filter
and is cleared by the toolbar's Clear action alongside the others.

---

# Sorting

Supported sort fields (backend, NULLS LAST):

- `created_at` (default, desc)
- `updated_at`
- `name`
- `overall_score` (via Scores column popover)
- `fit_score`
- `success_score`

Sorting is always performed by the backend. Rows where the sort column is empty
sort last in both directions.

---

# Data Refresh

The Refresh button in the Header reloads the current query. It calls the same
`refetch` used by the error-state Retry button, so it works from any state
(including the error state, where the header remains available). While a
refetch is in flight the button is disabled and its icon spins.

---

# Empty States

## No Companies

```text
No companies have been processed yet.
```

## No Search Results

```text
No companies match your search.

Try another keyword or remove filters.
```

---

# Loading States

## Initial Loading

- Skeleton rows

## Infinite Loading

```text
Loading more companies...
```

Existing rows remain interactive.

---

# Error States

## Backend Error

```text
Unable to load companies.

Retry
```

---

# Performance Requirements

The page must support

- Large company datasets
- Virtual scrolling
- Infinite loading
- Stable scroll position

The frontend never renders all rows simultaneously; only visible rows are
mounted.

---

# Related Documents

- `docs/api/companies/list-companies.md`
- `docs/ux/features/companies/company-row.md`
- `docs/ux/features/companies/company-detail.md`
- `docs/ux/features/companies/add-company.md`
- `docs/ux/features/jobs/processing-queue.md` (shared Processing Drawer)
- `docs/ux/flows/companies/browse-companies.md`
- `docs/ux/features/jobs/page.md` (reference: shared virtualized-table UX)
