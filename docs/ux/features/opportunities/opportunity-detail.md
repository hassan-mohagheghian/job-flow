# Opportunity Detail Drawer

## Purpose

Shows everything known about one inbound opportunity: the original message, extracted information with uncertainty, linked company/job, the current evaluation (scores + reasons), missing information, the application path, the recommended next action, and the evaluation history.

## Anatomy

```text
┌────────────────────────────────────────────────────────────┐
│ Senior Backend Engineer                    [Process]  ✕   │
│ Acme GmbH · Manual · Needs Info                            │
├────────────────────────────────────────────────────────────┤
│ ┌─ Score ────────────────────────────────────────────────┐ │
│ │ Overall 79 · Fit 85 · Success 70 · consider             │ │
│ │ Technical Match 88 · Experience 92 · Location ?        │ │
│ │ Concerns: sponsorship is unclear                       │ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌─ Next ─────────────────────────────────────────────────┐ │
│ │ Ask the recruiter for the location and JD              │ │
│ │ Path: Reply to the sender                              │ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌─ Original Message ─────────────────────────────────────┐ │
│ │ "Hi Hassan, we are hiring a Senior Backend Engineer…"  │ │
│ │ Jane · jane@acme.example · Senior Backend Engineer role│ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌─ Extracted ────────────────────────────────────────────┐ │
│ │ Role: Senior Backend Engineer (known)                  │ │
│ │ Company: Acme GmbH (inferred — needs verification)     │ │
│ │ Location: unknown · Skills: Python (known)             │ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌─ Links ────────────────────────────────────────────────┐ │
│ │ Job: Senior Backend Engineer → · Company: —            │ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌─ Missing ──────────────────────────────────────────────┐ │
│ │ Job location · Visa sponsorship                        │ │
│ └────────────────────────────────────────────────────────┘ │
│ ┌─ History ──────────────────────────────────────────────┐ │
│ │ eval-2 · ready_to_apply · 79 · 2h ago                  │ │
│ │ eval-1 · needs_info · — · 1d ago                      │ │
│ └────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────┤
│ Status: [Needs Info ▾]              [Delete opportunity]   │
└────────────────────────────────────────────────────────────┘
```

## Header

| Element     | Behavior                                              |
| ----------- | ----------------------------------------------------- |
| Title       | Extracted role, else subject, else `Unknown role`.    |
| Process     | Runs extract → resolve → evaluate; button spins while running. |
| Close       | Closes the drawer.                                    |

## Content

Sections render only when they have content, except Score (shows `Evaluation pending` + reason) and Next (always shows the recommended action). Uncertainty is shown inline (`known` values plain; `inferred` / `needs_verification` flagged). History lists evaluation snapshots newest first.

## Footer

Status select (funnel transitions; invalid ones rejected) and a delete button with confirmation.
