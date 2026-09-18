# Add Job Drawer

## Purpose

The Add Job Drawer allows users to create a new Job by providing the primary job posting URL, optional job information, additional reference links, and optional notes.

The drawer is the job variant of the shared **Create Entity drawer** (also used
by the Add Company drawer, see `docs/ux/features/companies/add-company.md`). Job
mode renders: Job Post URL → optional Job Title → Additional Links → Notes, with
**Add** and **Add & Queue** actions.

The drawer is opened from the **Jobs** page without leaving the current workspace.

A newly created Job can either:

- Be added to the Jobs list only.
- Be added to the Jobs list and immediately placed into the Processing Queue.

---

# Related Page

Opened from:

- `pages/jobs.md`

Uses:

- `design-system/drawer.md`

---

# Drawer

- Drawer (right side, vaul), default `lg` width — same reference layout as Job Details and Edit Job drawers
- Placement: `right`

---

# User Goals

The user should be able to:

- Import a new Job
- Provide the primary Job Post URL
- Optionally specify the Job Title
- Attach additional reference links
- Attach raw notes
- Choose whether processing should start immediately

---

# Opening the Drawer

The drawer can be opened four ways:

| Method                       | Description                                                    |
| ---------------------------- | -------------------------------------------------------------- |
| **Add Job button**           | Click the header button (shows an `N` shortcut hint).          |
| **`N` keyboard shortcut**    | Press `N` anywhere on the Jobs page (jobs-only). Ignored while typing inside an input, textarea, select, or content-editable element, and when a modifier key (Ctrl/Cmd/Alt/Meta) is held. |
| **Drag and drop**            | Drag a link from another tab onto the Add Job button or anywhere on the page (see `flows/jobs/drag-drop-job.md`). |
| **Ctrl/Cmd+V paste**         | Copy a job link anywhere, then press Ctrl+V / Cmd+V on the Jobs page with no editable element focused — the clipboard payload arrives via the `paste` event, so no `clipboard-read` permission is needed (see `flows/jobs/paste-to-add-job.md`). |

When the drawer opens, a URL copied to the clipboard is auto-filled into the
Job Post URL field (see Clipboard Prefill under Job Post URL). The clipboard is
read **inside the opening gesture** (the Add Job click or the `N` keypress), so
the `clipboard-read` permission is satisfied and the URL fills on the **first**
open. The drag-and-drop and Ctrl/Cmd+V entry points bypass the permission
entirely: they hand the captured URL straight to the drawer as a prop.

The **Job Post URL** input is **auto-focused** when the drawer opens, so the user
can type or press **Enter** (add & queue) immediately without clicking into the
field.

---

# Layout

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Add Job                                                          [Close]   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ Job Post URL *                                                             │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ https://...                                                           │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│ Tip: a copied link is auto-filled from your clipboard.                     │
│                                                                            │
│ Job Title (Optional)                                                      │
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ Senior Backend Engineer                                                │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│                                                                            │
│────────────────────────────────────────────────────────────────────────────│
│                                                                            │
│ Additional Links                                                           │
│                                                                            │
│ No additional links                                                        │
│                                                                            │
│                           [+ Add Link]                                     │
│                                                                            │
│────────────────────────────────────────────────────────────────────────────│
│                                                                            │
│ Notes                                                                      │
│                                                                            │
│ No notes                                                                   │
│                                                                            │
│                           [+ Add Note]                                     │
│                                                                            │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│                           [Cancel]                                         │
│             [Add]              [Add & Queue]                            │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

# Form Structure

```text
Add Job

├── Job Post URL *
├── Job Title (Optional)
├── Additional Links
└── Notes
```

---

# Job Post URL

The Job Post URL is the primary source of the Job.

This is the only required field.

Requirements

- Required
- Must be a valid URL

Examples

- LinkedIn Job
- Company Careers Page
- Greenhouse
- Lever
- Workday
- Ashby

## Clipboard Prefill

Every time the drawer opens, the Job Post URL field is **cleared first**, then a
URL is filled from the clipboard — if it holds a URL (matching `http(s)://…`),
that URL is pasted into the field. Any stale value from a previous interaction is
always replaced by the clipboard content. A hint under the field explains this:

```text
Tip: a copied link is auto-filled from your clipboard.
```

The clipboard is captured in the **opening gesture** (Add Job button click or `N`
keypress) and passed into the drawer, rather than read lazily after render. This
keeps the read inside the user activation so the browser's `clipboard-read`
permission is granted on the **first** open — the URL fills immediately instead
of requiring the user to close and reopen the drawer.

This makes the common "copy a job posting → press N → Add" flow effectively
three steps. An empty or non-URL clipboard is ignored silently (the field opens
empty).

The drag-and-drop and Ctrl/Cmd+V entry points skip this clipboard read: their
URL is already known when the drawer is told to open, and it flows in through
the same `clipboardUrl` prop. Pasting (or dropping) while the drawer is already
open replaces the field value through the same reactive path.

Because the clipboard is read fresh on **every** open, the prefill is **not**
suppressed after an Add — if the user copies another job link and opens the
drawer again, the new link fills immediately (no need to open twice).

---

# Job Title

Optional.

If left empty, the processing pipeline should automatically extract the title from the Job Post URL.

Examples

- Senior Backend Engineer
- Python Developer
- Staff Software Engineer

---

# Additional Links

Additional Links provide extra sources that may help processing.

This section starts empty.

```text
No additional links

                     [+ Add Link]
```

Selecting **Add Link** creates one new link item.

---

# Additional Link Item

```text
Title (Optional)

┌──────────────────────────────────────────────────────────┐
│ LinkedIn Profile                                         │
└──────────────────────────────────────────────────────────┘

URL *

┌──────────────────────────────────────────────────────────┐
│ https://...                                              │
└──────────────────────────────────────────────────────────┘

                                                [Remove]
```

Fields

| Field | Required |
| ----- | -------- |
| Title | No       |
| URL   | Yes      |

Example titles

- LinkedIn
- Company Website
- Recruiter Message
- Glassdoor
- Indeed
- Salary Page
- Engineering Blog

Rules

- URL is required.
- Title is optional.
- Empty items are not allowed.
- Remove unused items.

---

# Notes

Notes provide raw copied text that may help processing if the original pages become unavailable.

This section starts empty.

```text
No notes

                     [+ Add Note]
```

Selecting **Add Note** creates one new note item.

---

# Note Item

```text
Title (Optional)

┌──────────────────────────────────────────────────────────┐
│ Requirements                                              │
└──────────────────────────────────────────────────────────┘

Content *

┌──────────────────────────────────────────────────────────┐
│ Raw copied text...                                       │
│                                                          │
│                                                          │
└──────────────────────────────────────────────────────────┘

                                                [Remove]
```

Fields

| Field   | Required |
| ------- | -------- |
| Title   | No       |
| Content | Yes      |

Example titles

- Requirements
- Benefits
- Salary
- Company Description
- Personal Notes

Rules

- Content is required.
- Title is optional.
- Empty note items are not allowed.
- Remove unused items.

---

# Validation

## Job Post URL

- Required
- Must be a valid URL

---

## Job Title

- Optional

---

## Additional Links

- URL is required
- Title is optional

---

## Notes

- Content is required
- Title is optional

---

# Actions

| Action        | Description                                                     |
| ------------- | --------------------------------------------------------------- |
| Add           | Add a Job to the Jobs list                                      |
| Add & Queue   | Add a Job and immediately place it into the Processing Queue    |
| Enter (in Job Post URL or Job Title) | Shortcut for **Add & Queue** — adds the job and starts processing. |
| Cancel        | Close the Drawer                                                |
| Add Link      | Append a new Additional Link                                    |
| Remove Link   | Remove one Additional Link                                      |
| Add Note      | Append a new Note                                               |
| Remove Note   | Remove one Note                                                 |

---

# States

## Default

Empty form.

The Job Post URL field is pre-filled when the clipboard holds a URL.

---

## Editing

The user is entering information.

---

## Submitting

The form becomes read-only.

A loading indicator is displayed.

---

## Success (Add)

- Drawer closes.
- Job appears in the Jobs list.
- Status = **Imported**

---

## Success (Add & Queue)

- Drawer closes.
- Job appears in the Jobs list.
- Status = **Queued**
- Job is added to the Processing Queue.
- The Processing Queue drawer opens so the live workflow progress is visible immediately (instant processing workflow).
- The job's status transitions Queued → Running → Completed/Failed as the LangGraph job-processing workflow executes, streamed over SSE.

---

## Error

- Validation errors are displayed.
- Previously entered values are preserved.
- On duplicate URL (409 `JOB_ALREADY_EXISTS`): the error box shows the message
  plus an **"Open application"** link (navigates to `/jobs/<id>/application`).
  Below the error, a **summary card of the existing job** is rendered — the same
  top-of-detail block used by the job detail drawer — and a **"View full job
  details"** button opens the existing job's detail drawer so the user can
  review or reprocess it instead of importing a second copy.

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ ⚠ A Job with the same primary URL already exists.      Open application ↗ │
├────────────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────────────────────────┐ │
│ │ [A ] 85      90        80        #3               Open job posting ↗    │ │
│ │      Overall  Success   Fit       Rank                                   │ │
│ │                                                                         │ │
│ │ Senior Backend Engineer                                                  │ │
│ │  COMPANY      Acme GmbH             EMPLOYMENT   Full-time               │ │
│ │  TYPE         Product               SALARY       €90k                    │ │
│ │  LOCATION     Berlin                WORK TYPES   Remote                  │ │
│ │  VISA         Yes                                                        │ │
│ │  RECOMMENDATION [Apply]                                                  │ │
│ │  TRACKING→APPLICATION Ready to Apply / No application yet            │ │
│ │                                                                          │ │
│ │ View full job details ›                                                  │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

The summary payload comes from `error.details.job` (id, title, company,
company_type, location, visa, salary, employment/work types, Overall/Fit/Success
scores, rank, application state (`tracking_status`), recommendation, url). The
Recommendation row shows the AI recommendation badge (Apply / Consider / Skip)
when analysis has run, or "—" when no recommendation is available. The
Application row shows the `TrackingBadge` for the current application status, or
"No application yet" when the job has no application. "Open application" still
uses `error.details.job_id`.

---

# User Flow

## Add

```text
Open Drawer

↓

Enter Job Post URL

↓

(Optional)

Enter Job Title

↓

(Optional)

Add Additional Links

↓

(Optional)

Add Notes

↓

Add

↓

Job Added

↓

Status = Imported
```

---

## Add & Queue

```text
Open Drawer

↓

Enter Job Post URL

↓

(Optional)

Enter Job Title

↓

(Optional)

Add Additional Links

↓

(Optional)

Add Notes

↓

Add & Queue

↓

Job Created

↓

Status = Queued

↓

Added to Processing Queue

↓

Processing Queue drawer opens

↓

Instant workflow runs (fetch → extract → analyze → score → persist)

↓

Live progress streamed over SSE
```

---

# Responsive Behavior

## Desktop

- Right Drawer, default `lg` width (`720px`)

## Tablet

- Right Drawer, default `lg` width (`720px`)

## Mobile

- Right Drawer, default `lg` width, full-height

---

# Accessibility

- Keyboard navigation
- Focus trap
- Escape closes Drawer
- Screen-reader labels
- Required fields announced
- Validation messages associated with their inputs
- **Enter shortcut**: pressing Enter while the **Job Post URL** or **Job Title**
  input is focused adds the job and immediately queues processing (same as the
  "Add & Queue" button). The shortcut is ignored when the URL is invalid or empty.
  Note: Enter inside an open "Add Link" input submits that link (not the job).

---

# Related Documents

- `pages/jobs.md`
- `design-system/drawer.md`
