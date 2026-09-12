# Job Application Workspace Page

## Purpose

The Job Application Workspace is a dedicated full page at `/jobs/{job_id}/application`
that turns a job into an **application** and supports the "prepare and apply" journey.
It is a **consumer of existing Career Intelligence** — it reads the persisted job
analysis, company intelligence, candidate profile and skill evidence produced by the
existing pipeline and adds application-specific reasoning on top (roadmap, tailored
resume, cover letter, follow-ups). It never re-runs job/company/candidate analysis.

## Entry Points

- **Jobs page row action**: an airplane icon button (tooltip "Application") in every
  job row's action cell navigates to `/jobs/{id}/application`.
- **Job Detail drawer**: an "Application" button in the drawer header navigates to
  `/jobs/{id}/application`.

Both are available regardless of processing status.

## Core Principle

The workspace reads intelligence but never duplicates analysis:

| Data | Source endpoint | Used for |
| ---- | --------------- | -------- |
| Job identity + scores + recommendation | `GET /api/jobs/{id}` | Header |
| Job analysis (skills, summary, resume_fit) | `GET /api/jobs/{id}` (analysis) | AI generation context |
| Application record + follow-ups + documents + notes | `GET /api/applications/by-job/{id}` | Application/Documents/Notes sections |
| Roadmap | `GET /api/roadmaps/by-application/{id}` (404 when none) | Roadmap section |

Application generation (`roadmap`, `tailored_resume`, `cover_letter`) is queued via
`POST /api/applications/.../generate` (202) and runs asynchronously through the existing
processing pipeline with live SSE progress.

## High-Level Layout

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Back to Job      [Job Detail] [Job Edit] [Open job posting]            │
│ Staff Engineer · [Acme GmbH] · Berlin                    [Product Company]│
│ [Recommended] [Apply]     [A+] [Overall 90] [Success 88] [Fit 85] [#3]  │
├──────────────────────────────────────────────────────────────────────────┤
│ ▸ AI generation in progress ▸ 42% · "Generating tailored resume"        │  ← SSE card (while running)
│                                                                            (completed → "Generated successfully" + Dismiss)
├──────────────────────────────────────────────────────────────────────────┤
│ APPLICATION                                                            │
│  Status [ Recommended ▾]                                              │
│  APPLICATION TIMELINE                                                  │
│  [ Recommended ] [ 2026-08-11 09:00 ▾ ]                         [🗑]   │
│  [ Preparing   ] [ 2026-08-12 14:30 ▾ ]                         [🗑]   │
│  FOLLOW-UPS                                                            │
│  ☑ Follow up after interview · Sep 1, 2026                      [🗑]   │
│  [ Note (e.g. follow up after interview) ][ date ] [Add]               │
├──────────────────────────────────────────────────────────────────────────┤
│ ROADMAP                                                        [⚡ Gen]│
│  No roadmap yet. Generate a step-by-step job-preparation roadmap        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ Kafka → Staff Engineer Roadmap          [ACTIVE]                 │   │
│  │ Goal: Land a staff-level role                                    │   │
│  │ ▓▓▓▓▓░░░░░░ 25%  1/4 tasks done                                 │   │
│  │ MILESTONES  (overview — see roadmap-application-overview.md)     │   │
│  │ ① Skills foundation [IN PROGRESS][HIGH]      1/2  ▓▓▓▓░░░        │   │
│  │ ② Ship Kafka project [NOT STARTED][CRITICAL]  0/2  ░░░░░░░       │   │
│  │ [View roadmap] [⚡ Regenerate] [🗑 Delete]                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────────────┤
│ DOCUMENTS                                                                │
│ ┌────────────────────────────┐  ┌────────────────────────────┐           │
│ │ TAILORED RESUME v2  [copy] │  │ COVER LETTER v1    [copy]  │           │
│ │ [👁][download][edit][🗑][Regen]│  │ [👁][download][edit][🗑][Regen] │           │
│ │ │ markdown preview │       │  │ │ markdown preview │       │           │
│ └────────────────────────────┘  └────────────────────────────┘           │
├──────────────────────────────────────────────────────────────────────────┤
│ NOTES                                                                    │
│ ┌──────────────────────────────────────────────────────────────────────┐ │
│ │ What happened? (call, email, interview impression, decision…)        │ │
│ │                                                          [Add Note]  │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│  Recruiter call — positive, next step: tech interview                    │
│  Aug 21, 2026 14:02                                               [🗑]   │
│ ──────────────────────────────────────────────────────────────────────── │
│  Sent tailored resume via LinkedIn                                       │
│  Aug 20, 2026 09:47                                               [🗑]   │
└──────────────────────────────────────────────────────────────────────────┘
```

### Job Detail / Job Edit buttons

The header's top-right action group shows **Job Detail** and **Job Edit**
buttons (next to "Open job posting"). They open the shared `JobDetailDrawer` and
`JobEditDrawer` (the same drawers used on the Jobs page) with the current job,
so the user can inspect or edit the job without leaving the application page.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Back to Job              [Job Detail] [Job Edit] [Open job posting]    │
└──────────────────────────────────────────────────────────────────────────┘
       │  (click Job Detail / Job Edit opens the respective drawer overlay)
```

| Button | Behavior |
| ------ | -------- |
| Job Detail | Opens `JobDetailDrawer` for the job (same as the Jobs page detail drawer; includes Edit/Reprocess/Application actions). |
| Job Edit | Opens `JobEditDrawer` for the job; edits are persisted via `PUT /api/jobs/{id}` and the header refetches the job. |
| Back to Job | `router.push('/jobs?job={id}')`; the Jobs page opens the detail drawer for that job. |
| Open job posting | External link to `job.url` in a new tab. |
| Company name | When the job has a `company_id`, the header company name is a **link** to `/companies?company=<id>` (opens the company in the Companies page detail drawer). A **company type badge** renders beside the name when the linked company has a type. |
| Rank | A `[#N]` indicator after the Fit score shows the job's competition rank in the full job list sorted by overall, then success, then fit score (descending, NULLS LAST); jobs with identical scores share a rank. Sourced from `job.rank` on the detail response. |

## Component Hierarchy

```text
app/jobs/[job_id]/application/page.tsx        (dynamic route, first dynamic route)
└── widgets/job-application-workspace
    └── features/job-application
        ├── ApplicationWorkspace        → job + application queries, layout, sections
        │   ├── WorkspaceHeader         → back link, identity, status/recommendation badges, scores
        │   ├── GenerationProgress      → SSE generation status card
        │   ├── ApplicationSection      → titled card wrapper
│         ├── ApplicationTracker      → status select, status timeline, follow-ups
│         ├── RoadmapSection          → roadmap state + brief overview + generate/regenerate/delete
        │   └── ApplicationDocuments    → resume / cover letter cards
        │   └── ApplicationNotes       → free-text activity notes (add / delete, newest first)
        └── hooks/useApplicationGeneration → SSE subscription for the application
```

## States

### No application yet (empty state)

```text
┌──────────────────────────────────────────────────────────────┐
│                        [✈]                                   │
│                     No application yet                       │
│  Track this job as an application to prepare, generate a     │
│  tailored resume and cover letter, and schedule follow-ups.  │
│                     [Create Application]                     │
└──────────────────────────────────────────────────────────────┘
```

Clicking **Create Application** calls `POST /api/applications { job_id }` (201, status
`recommended`) and the workspace renders the three sections.

### Generation running

An in-place progress card (see `GenerationProgress`) appears above the sections while an
application execution is `queued`/`running` (driven by SSE), showing the current workflow
step title and percent. On `completed`/`failed` the application query is refetched so the
new roadmap/document appears; the card shows the result and a **Dismiss** button.

## Behaviors

| Element | Behavior |
| ------- | -------- |
| Back to Job | `router.push('/jobs?job={id}')`; the Jobs page opens the detail drawer for that job. |
| Status select | `PATCH /api/applications/{id}` with the chosen status; list: preparing, ready_to_apply, applied, interview, offer, accepted, rejected, withdrawn, expired. The change is recorded in the status timeline (time = now). |
| Status timeline | Each status node shows its time in an editable `datetime-local` input (`PATCH /api/applications/timeline/{id}`); a trash icon deletes the node (`DELETE /api/applications/timeline/{id}`). See `application-tracker.md`. |
| Follow-ups | Add (note + optional date), toggle done, delete — see `application-tracker.md`. |
| Roadmap Generate | `POST /api/applications/{id}/roadmap/generate` → 202 (`artifact="roadmap"`), SSE progress, roadmap refetch on completion. Label becomes **Regenerate** once a roadmap exists. |
| Roadmap Overview | When a roadmap exists the section shows a brief overview (title, goal, overall progress, first 5 milestones with status/priority/task progress) — see `roadmaps/roadmap-application-overview.md`. |
| Document Generate | `POST /api/applications/{id}/documents/{tailored_resume\|cover_letter}/generate` → 202, SSE progress, refetch on completion. Label becomes **Regenerate** once the document exists. |
| Document actions | Copy, download as `.md`, edit in place (textarea + Save/Cancel), delete. |
| Notes | Free-text activity notes with creation time, newest first; add via textarea + Add Note (or Enter), delete per note — see `application-notes.md`. |

## Loading States

- Job + application queries in flight → centered spinner.
- Generate buttons show a spinner and are disabled while queuing.
- Missing job (404) → "Unable to load the job."

## Error States

- Job fetch failure → "Unable to load the job."
- Generation failure → the `GenerationProgress` card shows the error message from the
  SSE `execution.failed` event; toast "Failed to queue …" on dispatch errors.
- Creating an application that already exists → backend 409/400 → error toast.

## Responsive Behavior

- Scores and status row wrap; the document grid collapses to one column below `xl`.
- `max-w-5xl` centered container.

# Related Documents

- `docs/ux/features/applications/application-tracker.md`
- `docs/ux/features/roadmaps/roadmap-generation.md`
- `docs/ux/features/roadmaps/roadmap-application-overview.md`
- `docs/ux/features/applications/application-documents.md`
- `docs/ux/features/applications/application-notes.md`
- `docs/ux/flows/applications/prepare-and-apply.md`
- `docs/ux/flows/applications/generate-application-artifacts.md`
- `docs/ux/flows/roadmaps/generate-roadmap-from-application.md`
