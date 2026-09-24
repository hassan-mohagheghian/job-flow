# Job Row

## Purpose

Defines the visual representation of a single Job inside the Jobs List.

The Jobs page is built from repeated Job Rows.

---

# Layout

Desktop

```
Title

Company

Location

Rank

Overall

Success

Fit

Recommendation

Tags

Processing

Updated
```

The layout is row-based.

Cards are intentionally not used.

Rows support dynamic height: when content in any column (especially Tags)
exceeds a single line, the row grows to accommodate up to two lines. Content
exceeding two lines is truncated with `...` and a downward caret icon at the
cell's end. The caret is purely visual — hovering the cell reveals the full
content via the browser's native title tooltip.

---

# Displayed Information

Each row displays:

- Job Title
- Company
- Location
- Remote badge
- Fit Score
- Success Score
- Overall Score
- Recommendation
- Tags (user-defined labels + dismissed/visa/easy_apply badges)
- Processing Status
- Last Updated
- Hover actions (revealed on row hover)

---

# Pin

The job row has **no** pin button. Pinned state is shown and toggled from the
**Job Details Drawer** header (see `features/jobs/pinned-job.md`).

---

# Recommendation

A compact badge showing the analysis recommendation derived from the Overall
Score:

| Recommendation | Meaning            | Color   |
| -------------- | ------------------ | ------- |
| Apply          | Overall ≥ 80       | Emerald |
| Consider       | Overall ≥ 60       | Amber   |
| Skip           | Otherwise          | Gray    |

Jobs without a completed analysis show an em dash (`—`) instead of a badge.

The badge is display-only: it is not clickable and does not open the Job
Details drawer.

# Score Presentation

Scores are displayed as compact badges, led by the overall grade badge
(derived from the overall score via the shared grade helper, `A++` … `D`).
The score values follow the same Overall → Success → Fit order and the same
color thresholds as the score cards in the Job Details drawer (see
`jobs/page.md`).

Example

Grade

A+

Overall

91

Success

88

Fit

94

```text
[A+]  O 91   S 88   F 94
```

Null scores show `—`; a missing overall score shows `—` for the grade instead
of `P`.

# Rank

The row's **Rank** (`#N`) is part of the score group, rendered as a compact
badge styled exactly like the `ScoreBadge`s (small `text-xs`, muted `#` label,
medium value) and placed right after the grade badge, before the Overall /
Success / Fit scores. Rank uses **competition ranking** (`RANK()`): jobs with
identical overall, success and fit scores share a rank, and the next distinct
rank skips ahead. It is the job's position in the full non-deleted job list
sorted by overall, then success, then fit score (each descending, NULLS LAST).

```text
[A+]  #7  O 91   S 88   F 94
```

The rank is absolute (independent of the list's current sort/filter) and is
sourced from the `rank` field on the list item. It is display-only; when a job
has no rank it is omitted.

---

# Processing Status

Displayed as a colored badge.

Possible values

- Queued
- Starting
- Running
- Completed
- Failed
- Cancelled

A job that has never been processed shows no processing badge (the list item
carries `latest_processing_execution = null`).

Running executions additionally display:

- spinner
- current progress

---

# Actions

There is **no fixed Actions column**. Hovering a row reveals a floating toolbar
of context-sensitive actions at the row's right edge (using a
`group`/`group-hover` pattern, overlaid on the row so the freed column width is
given to the data columns). All actions are **icon-only buttons with
tooltips**, keeping rows compact and scanable.

An **Edit** action is always available, allowing the user to update the Job's
core data (see `features/jobs/edit-job.md`).

A **Delete** action is always available, allowing the user to permanently remove
the Job and all its processing data (see `features/jobs/delete-job.md`).

No processing (never processed)

- Process (icon)
- Details (icon)
- Edit (icon)
- Delete (icon)

Running

- View Progress (icon)
- Edit (icon)
- Delete (icon)

Completed

- View Results (icon)
- Reprocess (icon)
- Edit (icon)
- Delete (icon)

Failed

- Retry (icon)
- Details (icon)
- Edit (icon)
- Delete (icon)

---

# Row Selection

Clicking anywhere on the row opens the Job Details Drawer.

Buttons do not trigger row selection.

---

# Hover Behavior

Hover highlights the entire row.

The current row becomes visually distinct.

---

# Live Updates

Rows update automatically using SSE.

The page must not reload.

Only the affected row should rerender.

When an execution reaches a terminal state, the list is refetched in the
background so the row shows the persisted pipeline output (extracted title,
final status) and stays correct across a reload.

---

# Responsive Behavior

Desktop

Full row layout.

Tablet

Some columns collapse.

Mobile

Rows become stacked.

Scores remain visible.

Actions stay icon-only (tooltips remain on tap).

---

# Accessibility

Rows support:

- keyboard navigation
- focus state
- screen readers

Buttons must remain individually accessible.

---

# Design Principles

The Job Row should prioritize:

- scanability
- information density
- fast comparison
- operational visibility

---

# Related Documents

- docs/ux/features/jobs/page.md
- docs/domain/jobs/job-list-item.md
- docs/api/jobs/list-jobs.md
