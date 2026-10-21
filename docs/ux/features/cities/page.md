# Cities Page

## Purpose

The Cities page is the workspace for browsing the normalized city catalog.

It shows every canonical `{city, country}` produced by the `CityNormalizer`,
with the number of linked jobs per city.

Users can:

- Browse normalized cities
- Search cities by city name, country, original text or address
- Sort cities by job count (default), country or city
- See the count of jobs linked to each city
- See the original source text / address for each city

The page is read-only: the catalog is derived from processing, not edited here.

The Cities page mirrors the Companies page UX: cursor-paginated list, infinite
scroll, and sortable column headers via the shared `SortableHeader`.

---

# Design Principles

The page follows these principles.

- The city is the primary grouping unit; job count is its main signal.
- Every city row is a unique canonical `{city, country}` (no duplicates).
- The page is read-only and derived from processing.
- Browsing is never blocked by background processing.

---

# High-Level Layout

```text
Cities Page

├── Header
├── Toolbar
└── City List
```

---

# Desktop Layout

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ ⛭ Cities (240)              Loaded 25 of 240                          ↻       │
├───────────────────────────────────────────────────────────────────────────────┤
│ Search city, country, original text…                                         │
├───────────────────────────────────────────────────────────────────────────────┤
│ City        │ Country  │ Jobs  │ Original                                     │
│─────────────│──────────│───────│──────────────────────────────────────────────│
│ Berlin      │ Germany  │ 161   │ Berlin, Germany                              │
│ Munich      │ Germany  │ 101   │ München, Germany                             │
│ Amsterdam   │ NL       │ 90    │ Amsterdam                                    │
│ Hamburg     │ Germany  │ 50    │ Hamburg, Germany                             │
│ (Remote)    │          │ 41    │ Remote                                       │
│ Utrecht     │ NL       │ 16    │ Utrecht, Netherlands                         │
│                                                                               │
│                                        Loading more cities...                 │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

# Primary Sections

## Header

Responsibilities

- Display page title and total count.
- Display loaded-vs-total count.
- Refresh the current result set.

Controls

| Control | Description                                                     |
| ------- | --------------------------------------------------------------- |
| Refresh | Reloads the current query (spins while a refetch is in flight). |

---

## Toolbar

Responsibilities

- Search cities.

Controls

| Control | Description                                              |
| ------- | -------------------------------------------------------- |
| Search  | Search by city, country, original text or address.       |

Search is debounced (300ms) via the shared `DebouncedInput` primitive. Pressing
`F` anywhere (unless inside an input/textarea/select/content-editable) moves
focus to the Search field and selects any existing query.

---

# City List

The City List is a row-based table (mirrors the Companies v2 table).

The frontend **does not use page numbers**.

Instead it uses **Infinite Loading** via cursor-based pagination, fed by
`GET /api/cities/list`.

The list preserves Search and Sorting while browsing.

---

# Infinite Loading

Loading sequence

```text
Open Cities

↓

Load first page (page_size=10)

↓

Render rows

↓

User scrolls

↓

Reach loading threshold (sentinel)

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
| Initial page size | 10               |
| Next page size    | 10               |
| Pagination        | Backend only     |
| Frontend UX       | Infinite Loading |

---

# Row Columns

| Column   | Description                                              |
| -------- | -------------------------------------------------------- |
| City     | Canonical city name, plus country badge.                 |
| Country  | Canonical country name.                                  |
| Jobs     | Number of linked, non-deleted jobs (sortable, default).  |
| Original | Original source text / address first seen for the city (large screens only). |

There is no `Actions` column and no detail drawer — the page is read-only.

---

# Column Details

## City

Displays the formatted `City, Country` (via the shared `formatCityLocation`
helper, the same presentation used in company rows and the company detail
drawer). A separate muted country label is shown beside it.

```text
Berlin       Germany
```

## Country

Displays the canonical country name.

```text
Germany
```

## Jobs

Displays the number of linked, non-deleted jobs for the city as a prominent
count, followed by a muted `jobs` label.

```text
161  jobs
```

This is the default sort column, descending (most jobs first).

## Original

Displays the first-seen `original_text` (falling back to `address`) truncated,
right-aligned. Hidden on smaller screens.

```text
Berlin, Germany
```

---

# Sorting

Supported sort fields (backend):

- `jobs` (default, desc)
- `country`
- `city`

Sorting is always performed by the backend. `jobs` sorts cities with the most
linked jobs first; zero-count cities sort last in both directions.

Clicking a header toggles `asc`/`desc`; clicking a new column sets it as the
active sort descending.

---

# Data Refresh

The Refresh button in the Header reloads the current query. It calls the same
`refetch` used by the error-state Retry button. While a refetch is in flight
the button is disabled and its icon spins.

---

# Empty States

## No Cities

```text
No cities yet
```

## No Search Results

```text
No cities match your search.
```

---

# Loading States

## Initial Loading

```text
Loading cities…
```

## Infinite Loading

```text
Loading more…
```

Existing rows remain interactive.

---

# Error States

## Backend Error

```text
Unable to load cities.

Retry
```

---

# Performance Requirements

The page must support:

- Large city datasets
- Infinite loading

The backend aggregates `job_count` in the same query (no N+1); the frontend
renders rows incrementally as pages load.

---

# Related Documents

- docs/api/cities/list-cities.md
- docs/domain/cities/cities.md