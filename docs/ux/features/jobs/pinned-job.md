# Pin Job

## Purpose

The Pin action lets the user mark a Job for attention so it can be found again
quickly through the Pinned filter.

Pinning is a lightweight, user-managed flag. It is independent of the analysis
pipeline and does not affect scoring or recommendation.

---

# Related Page

Located in:

- `features/jobs/page.md`

Triggered from the **Pin** button in the **Job Detail Drawer** header (the
drawer itself is documented in `features/jobs/page.md`).
There is no pin button on the job row itself.

Related:

- `api/jobs/list-jobs.md`

---

# Trigger

The **Pin** button is a pushpin icon in the drawer header, next to the
Reprocess and Edit actions.

- Empty pin: not pinned.
- Filled (primary color) pin: pinned.

---

# User Goals

The user should be able to:

- Pin a promising job for attention from its detail drawer
- Check whether an open job is pinned
- Unpin a job
- Show only pinned jobs via the toolbar filter

---

# States

## Idle

The drawer header shows an empty pin. Tooltip: *Pin job for attention*.

## Pinned

The drawer header shows a filled pin. Tooltip: *Unpin job*.

## Toggling

The pin updates **immediately** (optimistic update) before the request
finishes. `PUT /api/jobs/{job_id}/pinned` is sent to the server in the
background. The list row and the open detail payload are both patched
optimistically.

## Success

The pin keeps its new state and the list query is invalidated so pagination
and totals stay in sync with the server.

## Error

The pin is restored to its previous state (optimistic update rolled back) and
an error toast is shown.

---

# User Flow

```text
Open Jobs Page

↓

Open a job's details (click the row)

↓

Click the pin in the drawer header

↓

Pin toggles immediately (optimistic update)

↓

PUT /api/jobs/{job_id}/pinned { pinned: bool }

↓

Success: query invalidated in the background
```

---

# Pinned Filter

The toolbar's pushpin toggle restricts the list to pinned jobs.

```text
∘ All Jobs
pinned Pinned only
```

When the filter is active, pinning or unpinning a job refetches the list so
rows update immediately.

---

# Accessibility

- The icon button has an accessible label ("Pin job for attention" /
  "Unpin job").
- The pin exposes `aria-pressed` so screen readers announce the toggle state.

---

# Related Documents

- `features/jobs/page.md`
- `api/jobs/list-jobs.md`