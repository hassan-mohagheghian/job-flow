# Drag-and-Drop Link Import Flow

## Purpose

This flow describes how the user adds a new Job by **dragging a link from
another browser tab** into the app and dropping it onto **any page**.

The drop only **opens the Add Job drawer pre-filled** with the dropped URL. It
never auto-creates or auto-queues a job — the user then chooses **Add** (save
only) or **Add & Queue** (save + process) as usual.

---

## Trigger

The user drags a link from another tab (a job posting) into the app and drops
it anywhere on the current page — Jobs, Companies, Skills, Candidate, or any
other route.

A global drop surface (`GlobalAddJobProvider`, mounted in the app
`Providers`) is active on every route **except `/jobs*`**: the Jobs pages
keep their own page-local overlay + drawer (`DropJobOverlay` in the Jobs
widget), so the global surface disables itself there to avoid double overlays
or double drawers.

---

## Preconditions

- The dragged payload contains an `http(s)` URL (delivered by the browser via
  `text/uri-list` or `text/plain`).

---

## Drop Targets

```text
┌────────────────────────────────────────────────────────────────┐
│ Any page (Companies, Skills, …)                                 │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  …dragging a URL anywhere here shows a                   │  │
│  │     "Drop to add job" overlay (global, fixed)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                │
│  Jobs pages: same overlay, owned by the Jobs widget instead.   │
│  Add Job button (Jobs header): dedicated drop target.          │
└────────────────────────────────────────────────────────────────┘
```

---

## Flow

```text
On any page, drag a link from another tab

        │

        ▼

Hover over any point on the page   (/jobs*: page-local overlay instead)

        │

        ▼
"Drop to add job" indicator overlay            (global, fixed overlay;
                                                skipped when the drop was
                                                already handled, e.g. the
                                                Add Job button)
        │

        ▼
Drop the link

        │
        ▼
Extract http(s) URL from dataTransfer          (uri-list → text/plain)

        │

        ├────────────────────────── not a URL
        │        ignored (no action)
        │
        ▼
Valid URL

        │
        ▼
Open Add Job drawer, pre-filled with the URL

        │
        ▼
User presses "Add"  or  "Add & Queue"
        │               │
        ▼               ▼
  Save only         Save + process        (existing create-job / queue-job flow)
```

---

## Behavior Details

- **Pre-fill only.** Dropping never creates or queues a job. The Add Job drawer
  opens with the Job Post URL field filled in from the dropped URL; the user
  decides to Add or Add & Queue.
- **Dropping on the Add Job button** also opens the same pre-filled drawer. The
  button stops event propagation so the page-wide surface does not also fire.
- **Non-URL drops** (files, plain text without a URL) are silently ignored; no
  drawer opens, no error shown.
- **No backend change.** The drawer's existing `POST /api/jobs` with its `queue`
  flag already covers both Add and Add & Queue.

---

## States

| State                        | Description                                              |
| ---------------------------- | -------------------------------------------------------- |
| Dragging over button         | Button shows emerald ring; drawer not yet opened.        |
| Dragging over page           | "Drop to add job" overlay shown (non-interactive).       |
| Dropped URL                  | Add Job drawer opens with URL pre-filled.                |
| Dropped non-URL              | Nothing happens.                                         |
| Drawer Add                   | Job saved (Imported), list refreshed (existing flow).    |
| Drawer Add & Queue           | Job saved and queued, queue drawer opens (existing flow).|

---

## Related Documents

- `features/jobs/add-job.md`
- `flows/jobs/create-job.md`
- `flows/jobs/queue-job.md`
- `features/jobs/page.md`