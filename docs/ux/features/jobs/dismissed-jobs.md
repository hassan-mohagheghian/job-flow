# Dismiss Job

## Purpose

The Dismiss action lets the user mark a Job they are not interested in.
Dismissed jobs remain visible in the list but are highlighted with a red
"Dismissed" badge in the Processing column so they stand out from active jobs.

Dismissed is a lightweight, user-managed flag. It is independent of the analysis
pipeline and does not affect scoring or recommendation.

---

# Related Page

Located in:

- `features/jobs/page.md`
- `features/jobs/job-row.md`

Triggered from **Mark as dismissed** in the **Job Detail drawer** (`Actions`
group, second details column after Work Types), stacked under **Mark expired**.

Related:

- `api/jobs/list-jobs.md`

---

# Trigger

The **Mark as dismissed** button lives in the Job Detail drawer's `Actions`
row, below **Mark expired** and after **Work Types**. It is only shown for
non-dismissed jobs; a dismissed job shows **Undismiss** in the same slot.

Opening the dialog never changes the job by itself — only the dialog's
**Dismiss** action calls the API.

---

# User Goals

The user should be to:

- Dismiss a job they are not interested in with an optional reason
- See at a glance which jobs are dismissed (red badge in status column)
- Dismissed jobs stay in the list for context

---

# User Flow

```text
Open Jobs Page

↓

Open a Job Row → Job Details drawer

↓

Click Mark as dismissed (Actions group in the second column)

↓

Dismiss Dialog opens

  ┌─ Dismiss job ──────────────────────────┐
  │ Dismiss "Senior Engineer"?             │
  │ It will be marked as dismissed...       │
  │                                         │
  │ ┌───────────────────────────────────┐   │
  │ │ Why are you dismissing this?      │   │
  │ │ (optional)                        │   │
  │ └───────────────────────────────────┘   │
  │                     [Cancel] [Dismiss]  │
  └─────────────────────────────────────────┘

↓

User types a reason (optional) and clicks Dismiss

↓

PUT /api/jobs/{job_id}/dismissed { dismissed: true, note: "..." }

↓

Success:
- Job row shows red "Dismissed" badge in the Tags column
- The drawer's Mark as dismissed button becomes Undismiss
- If note was provided, it is appended to the job's notes
```

## Undismiss

Clicking **Undismiss** in the same `Actions` slot calls
`PUT /api/jobs/{job_id}/dismissed { dismissed: false }` immediately (no dialog),
removes the red badge and restores **Mark as dismissed**.

---

# Dismiss Dialog

The dialog appears when the user clicks the dismiss button.

## Layout

```text
┌─ Dismiss job ──────────────────────────┐
│                                        │
│ Dismiss "Senior Engineer"?             │
│ It will be marked as dismissed in      │
│ the list.                              │
│                                        │
│ ┌───────────────────────────────────┐  │
│ │ Why are you dismissing this?      │  │
│ │ (optional)                        │  │
│ └───────────────────────────────────┘  │
│ Ctrl+Enter to dismiss                  │
│                                        │
│                     [Cancel] [Dismiss] │
└─────────────────────────────────────────┘
```

## Controls

| Control  | Description                                      |
| -------- | ------------------------------------------------ |
| Textarea | Optional reason for dismissal (free text)        |
| Cancel   | Closes the dialog without dismissing             |
| Dismiss  | Dismisses the job and optionally saves the note  |

## Keyboard

- `Ctrl+Enter` / `Cmd+Enter` — Dismiss
- `Escape` — Cancel

---

# States

## Idle

The drawer's `Actions` row shows **Mark expired** and **Mark as dismissed**
stacked. A dismissed job shows **Undismiss** instead of **Mark as dismissed**.

## Dialog Open

The dismiss dialog is shown. The textarea is focused automatically.

## Dismissing

The Dismiss button in the dialog shows a loading state.

## Success

- The drawer's button becomes **Undismiss**
- A red "Dismissed" badge appears in the Tags column
- If a note was provided, it is appended to the job's notes

---

# Dismissed Status

Dismissed jobs show a red "Dismissed" badge in the Processing column instead of
their processing status.

```text
┌──────────────┐
│ Dismissed    │   (red badge, bg-red-500/10, text-red-500)
└──────────────┘
```

The badge uses:
- Background: `bg-red-500/10`
- Text: `text-red-500`
- Border: `border-red-500/20`

---

# Accessibility

- The dismiss button is labelled **Mark as dismissed** / **Undismiss**.
- The dialog has a clear title and description.
- The textarea is auto-focused when the dialog opens.
- Cancel and Dismiss buttons are keyboard accessible.

---

# Related Documents

- `features/jobs/page.md`
- `features/jobs/job-row.md`
- `api/jobs/list-jobs.md`

---

# State Diagram

```mermaid
stateDiagram-v2
    [*] --> NotDismissed
    NotDismissed --> DialogOpen: Click dismiss button
    DialogOpen --> NotDismissed: Cancel / Escape
    DialogOpen --> Dismissed: Click Dismiss / Ctrl+Enter

    state "NotDismissed" as NotDismissed {
        state "× button visible" as bv
        state "Normal processing status" as nps
    }

    state "DialogOpen" as DialogOpen {
        state "Textarea for note" as tn
        state "Cancel + Dismiss buttons" as cb
    }

    state "Dismissed" as Dismissed {
        state "Red Dismissed badge in status" as rdb
        state "× button hidden" as bh
        state "Note appended to job notes" as np
    }
```
