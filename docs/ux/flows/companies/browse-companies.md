# Browse Companies

## Purpose

How a user discovers, filters, and opens companies in the Companies workspace.

---

# Flow

```text
Open Companies page
        │
        ▼
Load first page (GET /api/companies/list, page_size=10)
        │
        ▼
┌─────────────────────────┐
│  Browse / Manage        │
│                         │
│  Search / Filter / Sort │
│  Scroll (infinite)      │
│  Open row → Detail      │
└────────────┬────────────┘
             │
             ▼
   ┌──────────────────┐   ┌──────────────────────────────┐
   │  Detail Drawer   │   │  Processing Drawer (shared,  │
   │  (Drawer)        │   │  targetType=company, live SSE)│
   │  Reprocess/Edit  │   │  Start / Retry / Remove /     │
   │  Links column    │   │  Cancel                       │
   └──────────────────┘   └──────────────────────────────┘
```

---

# Steps

## 1. Open the Companies page

The page mounts, calls `GET /api/companies/list` for the first page, and
renders the virtualized table.

## 2. Search

Typing in the search box (debounced 300ms) refetches the list with the `query`
parameter. Supported fields: name, industry, city, country, description.

## 3. Filter by industry

Selecting an industry in the toolbar refetches the list with the `industry`
parameter.

## 3b. Filter by status

Selecting a processing status in the toolbar refetches the list with the
`status` parameter. The status is derived from the company's **latest
processing execution** (the same source and `ExecutionStatus` vocabulary as
jobs); `status=none` selects companies with no execution ("Not processed").

## 4. Sort

Clicking a sortable header (Name, Updated) or the Scores popover (Overall /
Fit / Success) refetches with the chosen `sort` and `order`.

## 5. Scroll

Reaching the sentinel fetches the next page with the cursor. Rows append until
`has_more` is false.

## 6. Open company details

Clicking a row opens the Company Detail drawer. The `?company=` URL parameter
is set, so the drawer survives a reload (deep-link).

## 7. Manage

From the drawer header the user can reprocess or edit the company. Reprocess
calls `POST /api/companies/{id}/reprocess` (returns `{status: "queued",
execution_id}`) and opens the shared Processing Drawer (`targetType="company"`)
where the new execution can be monitored. Deletion is no longer available inside
the detail drawer — it happens only via the row actions on the Companies page.

## 8. Monitor processing

The header Queue button opens the shared Processing Drawer filtered to
companies, showing Running / Waiting / Failed executions with live SSE progress
(`/events/processing`, `target_type: "company"`).

---

# Edge Cases

## Deep link

Opening `/companies?company=42` opens the detail drawer for company 42 on mount.

## Deleting the open company

The detail and edit drawers close; the `?company=` parameter is cleared.

## No results

An empty list shows the "No companies have been processed yet." empty state.

## Search with no matches

Rows disappear and the empty state shows; the Clear button in the toolbar
restores the full list.

---

# Related Documents

- `docs/ux/features/companies/page.md`
- `docs/api/companies/list-companies.md`
