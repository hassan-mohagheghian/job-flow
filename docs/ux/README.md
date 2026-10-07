# UX Documentation

This directory contains the product and UX specifications for **Job Search Intelligence**.

## Purpose

UX docs define how the application should look and behave. They are organized in three layers:

| Directory                | Scope                                             |
| ------------------------ | ------------------------------------------------- |
| `docs/ux/design-system/` | Reusable UI primitives (Drawer, buttons, ...)     |
| `docs/ux/features/`      | Component and page specifications per feature     |
| `docs/ux/flows/`         | End-to-end user flows (steps, states, edge cases) |

## How To Read

- **Features** describe *what* a component shows (fields, sections, actions, states).
- **Flows** describe *how* a user accomplishes a goal from start to finish.
- **Design system** documents shared primitives used across all features.

Flow documents reference feature documents, and feature documents reference the design system.

## Index

```text
docs/ux/
├── README.md                  ← this index
├── design-system/
│   ├── drawer.md              Drawer (variants, placement, anatomy)
│   ├── input.md               DebouncedInput (text search / filter inputs)
│   └── README.md
├── app-shell.md               Left sidebar nav (rail + collapse + mobile sheet)
├── features/
│   ├── applications/
│   │   ├── workspace.md         Job Application Workspace page (header, sections, SSE progress)
│   │   ├── application-tracker.md  Status select, status timeline (edit/delete nodes), follow-ups
│   │   └── application-documents.md  Tailored resume / cover letter cards (incl. Download PDF)
│   │   └── application-notes.md  Free-text activity notes (add / delete, newest first)
│   ├── placeholders/
│   │   └── placeholders.md      Placeholders page (personal-detail form)
│   ├── roadmaps/
│   │   ├── my-roadmaps.md       My Roadmaps list page (cards, create/edit/delete, empty)
│   │   ├── roadmap-detail.md    Roadmap detail page (goal header, milestone journey, tasks, notes/resources/skills)
│   │   ├── roadmap-generation.md  Application Workspace roadmap section (generate/regenerate/view/delete)
│   │   ├── roadmap-application-overview.md  Brief roadmap overview (milestones list) in the workspace
│   │   └── roadmap-create-edit.md  Manual create/edit dialogs
│   ├── ai/
│   │   ├── llm-configurations.md
│   │   ├── add-llm-configuration.md
│   │   ├── edit-llm-configuration.md
│   │   ├── view-llm-configuration.md
│   │   ├── enable-llm-configuration.md
│   │   ├── disable-llm-configuration.md
│   │   └── delete-llm-configuration.md
│   ├── companies/
│   │   ├── page.md            Companies page (list, toolbar, column toggles, infinite scroll, drawers)
│   │   ├── company-row.md     Company row columns, grades, scores, status, actions
│   │   ├── company-detail.md  Company Detail drawer (single page, scores, header actions)
│   │   ├── relate-company.md  Related companies: main/alias relations, Relate Company dialog
│   │   ├── add-company.md     Add Company drawer (shared Create Entity, company mode)
│   │   ├── edit-company.md    Edit Company drawer
│   ├── cities/
│   │   └── page.md            Cities page (read-only catalog, sortable columns, infinite scroll)
│   ├── candidate/
│   │   └── profile-import.md  Candidate Profile Import page (sources, analyze, review)
│   └── jobs/
│       ├── page.md            Jobs page (list, toolbar, column toggles, infinite scroll)
│       ├── job-created-timeline.md  Jobs created-per-day side panel (month dividers, own scroll)
│       ├── tracking.md        Job tracking status (application funnel column + filter)
│       ├── job-row.md         Job row columns and scores
│       ├── pinned-job.md      Pin a job for attention (replaces favorite)
│       ├── dismissed-job.md  Hide a job from the default list
│       ├── job-tags.md       User-defined tags with multi-select filter
│       ├── add-job.md         Add Job drawer (shared Create Entity, job mode)
│       ├── edit-job.md        Edit Job drawer
│       ├── delete-job.md      Delete Job
│       ├── processing-queue.md
│       └── workflow-progress.md
│   ├── opportunities/
│       ├── page.md            Opportunities page (inbound list, toolbar, drawers)
│       └── opportunity-detail.md  Opportunity Detail drawer (message, extracted, score, path, history)
│   ├── rules/
│       ├── page.md            Rules page (scopes, columns, priority/badge, reorder)
│       └── rule-form-drawer.md  Add / Edit Rule right drawer
│   └── skills/
│       ├── page.md            Skills page (list, toolbar, multi-select, column toggles, infinite scroll, drawers)
│       ├── skill-row.md       Skill row columns, select checkbox, origin/alias badges, mentions, actions
│       ├── skill-detail.md    Skill Detail drawer (level, roles, tags, aliases, referenced jobs)
│       ├── skill-resources.md Notes & links for tracking learning progress
│       ├── add-skill.md       Add Skill drawer (name, level, category, roles, path)
│       ├── edit-skill.md      Edit Skill drawer (aliases, merge, make canonical)
│       └── breakdown-skill-dialog.md  Break down a composite skill into atomic children
└── flows/
    ├── applications/
    │   ├── prepare-and-apply.md  Create/track an application (status, applied, follow-ups)
    │   └── generate-application-artifacts.md  Generate + watch roadmap/resume/cover letter
    ├── roadmaps/
    │   ├── create-manual-roadmap.md  Create a manual roadmap + first milestone/task
    │   └── generate-roadmap-from-application.md  Generate AI roadmap, watch SSE, open detail
    ├── candidate/
    │   └── import-profile.md  Import resume/LinkedIn, analyze, review profile
    ├── companies/
    │   ├── browse-companies.md  Browse, search, filter, sort, open details
    │   ├── relate-company.md    Relate an alias company to a main (consolidate duplicates)
    ├── jobs/
    │   ├── browse-jobs.md     Browse, search, filter, sort
    │   ├── create-job.md      Create job (import only)
    │   ├── queue-job.md       Create job + immediately queue (instant workflow)
    │   ├── edit-job.md        Edit a job's core data
    │   ├── delete-job.md      Delete a job
    │   ├── process-job.md     Start processing
    │   ├── process-job-live.md
    │   ├── processing-queue.md
    │   ├── drag-drop-job.md   Import by dragging a link onto the page
    │   ├── paste-to-add-job.md  Import by pressing Ctrl/Cmd+V with a copied link
    │   └── ...
    ├── opportunities/
    │   └── process-inbound.md  Paste a message, process, follow the next action
    ├── rules/
        └── reorder-rules.md   Move up/down + drag reorder, priority math, clamping
    └── skills/
        ├── browse-skills.md   Browse, search, filter, sort, open details
        ├── merge-skills.md    Merge skill(s) into a canonical one (single or bulk)
        └── breakdown-skill.md Break a composite skill into atomic children
```

## Current Focus

The current product focus is the **Jobs** workspace:

- Browse jobs with infinite scrolling (`docs/ux/features/jobs/page.md`).
- Import jobs via the Add Job drawer (`docs/ux/features/jobs/add-job.md`).
- Import a job by dragging a link into the page (`docs/ux/flows/jobs/drag-drop-job.md`).
- Import a job by pressing Ctrl/Cmd+V with a copied link (`docs/ux/flows/jobs/paste-to-add-job.md`).
- Edit job core data (`docs/ux/features/jobs/edit-job.md`).
- Delete a job and all its processing data (`docs/ux/features/jobs/delete-job.md`).
- Monitor AI processing through the Processing Queue (`docs/ux/features/jobs/processing-queue.md`, `docs/ux/flows/jobs/processing-queue.md`).
- Watch live workflow progress (`docs/ux/flows/jobs/process-job-live.md`).

**Applications** is the newest module (140): a per-job Application Workspace
(`/jobs/{id}/application`) for tracking status/follow-ups and generating a roadmap,
tailored resume and cover letter (`docs/ux/features/applications/`,
`docs/ux/features/roadmaps/`, `docs/ux/flows/applications/`, `docs/ux/flows/roadmaps/`).

**Candidate** (110 Phase 1): import resume/LinkedIn, run
AI profile analysis and review the canonical profile
(`docs/ux/features/candidate/profile-import.md`,
`docs/ux/flows/candidate/import-profile.md`).

## Design Language

- Built on **shadcn/ui** + Tailwind CSS.
- Custom density tokens `text-3xs` (6px) / `text-2xs` (8px).
- Status colors: gray (ready), blue (queued), cyan (running), green (completed), red (failed), orange (cancelled).
- Score grades: A++/A+ green, A lime, B blue, C orange, D red.
- All UI is keyboard accessible and follows WCAG AA.

For the visual design summary and wireframes see `docs/ux/DESIGN.md`.
