# Product & UX Design

## Design Language

Job Search Intelligence is a **dense, data-focused dashboard** built for software engineers comparing many job opportunities at once.

- **UI library**: shadcn/ui primitives (Radix UI + Tailwind CSS)
- **Icons**: Lucide
- **Density tokens**: custom Tailwind font sizes `text-3xs` (6px) and `text-2xs` (8px) for compact tables and cards
- **Status colors**: Ready (gray), Queued (blue), Running (cyan), Completed (green), Failed (red), Cancelled (orange)
- **Score grades**: A++ / A+ (green), A (lime), B (blue), C (orange), D (red)

The interface follows WCAG AA: keyboard navigation, focus management, screen-reader labels, and ARIA progress indicators.

---

## Navigation Structure

Navigation is a **left sidebar rail** on desktop (`lg+`), collapsible to an
icon-only rail. On mobile (`<lg`) the rail collapses into a hamburger (top-left
of a slim top bar) that opens a left sheet with the same items.

```
SIDEBAR RAIL
  ├── Job Search (brand → /jobs)
  ├── Jobs           Job list (infinite scroll) + Processing Queue drawer
  ├── Companies      Company intelligence + processing queue
  ├── Cities         Normalized city catalog (read-only)
  ├── Skills         Skill management, aliases, insights
  ├── Candidate      Candidate profile import + review
  ├── Placeholders   Personal-detail {{token}} values for generated documents
  ├── Rules          Scoring rules configuration
  └── AI ▾           Inline expandable submenu
      └── LLM Configurations
  ──────────────────────────
  ├── Theme toggle   (bottom cluster)
  ├── Generation History (bottom cluster)
  └── Collapse toggle   (w-60 ⇄ w-[68px] icon rail, persisted)

MOBILE (<lg): hamburger → left Sheet with the same nav + bottom cluster.
```

Per-job detail pages (e.g. the Application Workspace at `/jobs/{id}/application`)
are reached from within the Jobs workspace — the rail highlights Jobs and the page
offers a "← Back to Job" link (`/jobs?job={id}`), which reopens the Job Details
drawer for that job.

---

## Design System

### Drawer

The Drawer is the primary secondary workspace. It opens without leaving the current page.

| Variant | Width | Typical Usage        |
| ------- | ----: | -------------------- |
| xs      | 320px | Confirmations        |
| sm      | 420px | Filters, simple forms |
| md      | 560px | Processing Queue     |
| lg      | 720px | Company Details      |
| xl      | 960px | Job Details          |
| full    |  100% | Mobile / full screen |

Placement is right by default; all variants become full-screen on mobile.

---

## Wireframes

### Jobs Page

```text
┌─────────────────────────────────────────────────────────────────────────────────────┐
│ Jobs                                          Queue (2 Running · 4 Waiting)  + Import │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ Search .......................................................................       │
│ Sort ▼                  Filters ▼                                        Refresh     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ # │ Job                  │ Company    │ Location │ Scores        │ Tags         │ Rec │ Tracking│ Proc.  │ Updated │
│─────────────────────────────────────────────────────────────────────────────────────────────────────────────│
│ 1 │ Senior Backend Eng.  │ GetYourGuid│ Berlin   │ [A++] #2 O 94 S 91 F 95 │ [python] [remote] │ Apply│ [Applied]│ Ready  │ 2m      │
│ 2 │ Backend Engineer     │ Karla      │ Berlin   │ [A+] #5 O 90 S 88 F 90  │ [java]    │ Apply│ [Interview]│ Running│ now    │
│ 3 │ Python Developer     │ Flexa      │ Remote   │ [A] #9 O 83 S 84 F 86   │            │ Skip │ [Not Applied]│ Dismissed│ 5m   │
│                                                                                     │
│                                       Loading more jobs...                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

A **Jobs Created Timeline** panel (`job-created-timeline.md`) sits on the right
edge of the page, beside the list. It shows the number of jobs created per day
(newest first) with month dividers ("Aug 2026"), has its own scroll, and is
independent of the list's filters/pagination.

There is **no dedicated Actions column**. Job row actions (Process / Reprocess /
Retry / Cancel / Details / Application / Edit / Delete) are revealed as a
floating toolbar at the right edge of the row on hover (`group-hover`), freeing
the column width for the data columns. The same hover-reveal pattern applies to
Companies and Skills rows.

### Processing Queue Drawer

```text
┌─────────────────────────────────────────────┐
│ Processing Queue                      Close │
├─────────────────────────────────────────────┤
│ Processing (2)                              │
│ ┌─────────────────────────────────────────┐ │
│ │ Senior Backend Engineer                 │ │
│ │ Fetching Sources                        │ │
│ │ ██████████████░░░░ 60%                  │ │
│ │                             Details    │ │
│ └─────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────┐ │
│ │ Data Engineer                            │ │
│ │ ░░░░░░░░░░░░░░░░░ 0%                     │ │
│ └─────────────────────────────────────────┘ │
│ Queued (3)                                  │
│ ┌─────────────────────────────────────────┐ │
│ │ Python Developer                        │ │
│ │ Position #1                             │ │
│ │                        Start    Remove  │ │
│ └─────────────────────────────────────────┘ │
│ Failed (1)                                  │
│ ┌─────────────────────────────────────────┐ │
│ │ Frontend Engineer                       │ │
│ │ Failed to fetch source                  │ │
│ │                         Retry   Remove  │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Add Job Drawer (Create Entity — job mode)

```text
┌─────────────────────────────────────────────┐
│ Import Job                          [Close] │
├─────────────────────────────────────────────┤
│ Job Post URL *                              │
│ ┌─────────────────────────────────────────┐ │
│ │ https://...                             │ │
│ └─────────────────────────────────────────┘ │
│ Job Title (Optional)                        │
│ ┌─────────────────────────────────────────┐ │
│ │ Senior Backend Engineer                 │ │
│ └─────────────────────────────────────────┘ │
│ Additional Links                     [+Add] │
│ No additional links                         │
│ Notes                                [+Add] │
│ No notes                                    │
│ ⚠ URL already exists.  Open existing job    │
├─────────────────────────────────────────────┤
│                    [Cancel] [Add] [Add & Queue]│
└─────────────────────────────────────────────┘
```

On duplicate URL (409) the error box adds an **Open existing job** link that
navigates to `/jobs?job=<id>` (id from `error.details.job_id`) and opens the
existing job's detail drawer.

### Drag-and-Drop Job Import

The Jobs page accepts a link dragged from another browser tab. Dropping it on
the **Add Job** button or **anywhere on the page** opens the Add Job drawer
pre-filled with that URL — nothing is auto-created or auto-queued; the user then
presses **Add** or **Add & Queue** (see `flows/jobs/drag-drop-job.md`).

```text
 Drag a link from another tab ──► Jobs page
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
   Drop on Add Job            Drop on page            Drop elsewhere
   button highlights          "Drop to add job"       (non-URL) ignored
   (emerald ring)             overlay shown
        │                          │
        └─────────────┬────────────┘
                      ▼
        Add Job drawer opens, Job Post URL pre-filled
                      │
              ┌───────┴───────┐
              ▼               ▼
           [Add]          [Add & Queue]
        (save only)     (save + queue)
```

The page-wide drop surface and the button are the only drop targets; non-URL
drops are silently ignored.

### Paste-to-Add Job (Ctrl/Cmd+V)

The Jobs page also accepts a copied link via **Ctrl+V / Cmd+V**: with no
editable element focused, the Add Job drawer opens pre-filled with the pasted
URL. The payload comes from the `paste` event (no clipboard permission);
non-URL content and pastes inside inputs keep the browser's native behavior.
Nothing is auto-created or auto-queued (see `flows/jobs/paste-to-add-job.md`).

```text
 Copy a job link anywhere ──► Jobs page ──► Ctrl/Cmd+V
                                              │
              ┌───────────────────────────────┼──────────────────────────┐
              ▼                               ▼                          ▼
     Focus in an input/            clipboard holds http(s) URL   clipboard without URL
     textarea (search, drawer)     drawer opens, Job Post        nothing happens
     native paste into field       URL pre-filled                (native behavior)
              │                               │
              │                    ┌──────────┴──────────┐
              │                    ▼                     ▼
              │                 [Add]               [Add & Queue]
              │              (save only)          (save + queue)
```

### Edit Job Drawer

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Edit Job                                                      [Close]│
├──────────────────────────────────────────────────────────────────────┤
│ Title (Optional)                                                     │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Staff Software Engineer                                          │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ Role (Optional)                                                     │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │                                                                  │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ Company (Optional)                                                  │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Acme GmbH                                                        │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ Location (Optional)                                                 │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Berlin                                                           │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ Job Post URL *                                                     │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ https://...                                                      │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ Work Type        Employment Type                                   │
│ ┌─────────────┐  ┌──────────────┐                                  │ │
│ │ On-site    ▾│  │ Full-time   ▾│                                  │ │
│ └─────────────┘  └──────────────┘                                  │ │
│ Visa (Optional)     Salary (Optional)                              │
│ ┌─────────────┐  ┌──────────────┐                                  │ │
│ │ Strong      │  │ €90k - €110k  │                                  │ │
│ └─────────────┘  └──────────────┘                                  │ │
│ Description                                                        │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Work alongside a cross-functional team...                       │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ Notes (editable, add/remove)                                       │
│ Additional Links (editable, add/remove)                            │
├──────────────────────────────────────────────────────────────────────┤
│                              [Cancel]                        [Save]  │
└──────────────────────────────────────────────────────────────────────┘
```

### Job Details Drawer

Shows the full record for a row, including the AI Analysis block produced by
the Job Analysis phase. The Analysis section renders only once the analysis
phase completes (data is refetched on the `execution.completed` SSE event).

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ Job Details                      [Application] [↻] [Edit] [Close]│
├───────────────────────────────────────────────────────────────────────────────┤
│ [B]  Fit 85   Success 70   Overall 79   #3   [Why]               │
│                                                                              │
│ Senior Backend Engineer                                                      │
│ Company   Acme Inc →▾   │ Employment  Permanent                            │
│ Location  Berlin, DE…    │ Salary      90k                                  │
│ Work Types Hybrid, FT    │ Visa        EU Blue Ca… (hover/click → full)    │
│ Open job posting ↗                                                          │
│                                                                              │
│ ┌─ Recommendation ─────────────────────────────────────────────────────────┐ │
│ │ [consider]           2026-08-03 12:00                                    │ │
│ │ Great role overall. It matches the senior backend profile...             │ │
│ └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌─ Tagged Skills ──────────────────────────────────────────────────────────┐ │
│ │ [Python · L4 · Language] [Postgres · L4 · Data]                          │ │
│ │ [Kafka · L1 · Data] [Docker · L3 · Engineering]                          │ │
│ └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ┌─ AI Analysis ────────────────────────────────────────────────────────────┐ │
│ │ • Mention Kafka coursework                                               │ │
│ │ • Ask about salary band                                                  │ │
│ ├─ Summary ────────────────────────────────────────────────────────────────┤ │
│ │ Backend role at Acme.                                                    │ │
│ │ Resume fit: Strong fit.  Note: Apply early.                              │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│ ▸ Published by — RecruitCo, TalentBridge GmbH                                │
│                                                                              │
│ ▸ Processing                                                                 │
│                                                                              │
│ ┌─ Description ─────────────────────────────────────────────────────────────┐ │
│ │ We need a senior backend engineer with Python, Postgres and Kafka.        │ │
│ └────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────────────────┘
```

The `recommendation` badge maps apply → green, consider → blue, skip → gray.
The `[#N]` indicator after the Overall score shows the job's competition rank
in the full job list sorted by overall, then success, then fit score
(descending, NULLS LAST); jobs with identical scores share a rank.
The `[Why]` button after the Overall score opens a **Scores Explanation**
popover (Why it fits / Chance of success / Concerns). It auto-opens on hover,
auto-closes on unhover, and clicking pins/unpins it. Below the title a
balanced two-column block (each half the drawer width) shows six labeled rows,
three per column: `Company` (picker) / `Location` / `Work Types` on the left;
`Employment` / `Salary` / `Visa` on the right. Rows are aligned one-to-one
across the columns. `Location` and `Visa` are truncated at 30 characters with
an ellipsis; hovering reveals the full value in a tooltip and clicking
expands/collapses the value inline. When the job's linked company has a
**company type**, a `Type` detail row renders right below the Company row.
Tagged skills render as compact badges;
`missing`/`low` skills are tinted to signal
gaps. The **Published by** section is a collapsed-by-default `Collapsible`
whose folded trigger shows the recruiter company names inline, positioned just
before the **Processing** collapsible. Full specs live in
`docs/ux/features/jobs/`.

---

### Rules Page

Each rule has a single `priority` (0–100) that drives list order, the severity
badge, and the LLM weight (`w:{n}`). Rules are grouped into scope columns.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Scoring Rules                                    (e.g. 17/20 active)          │
├──────────────────────────────────────────────────────────────────────────────┤
│ [All] [Shared] [Jobs] [Product Company] [Recruiting]                         │
├──────────────┬──────────────┬───────────────┬───────────────┬───────────────┤
│ SHARED Rules │  JOB Rules   │ Product Co... │ Recruiting... │               │
│ (4/4)        │  (7/7)       │   (5/5)       │   (4/4)       │               │
│ + Add rule   │ + Add rule   │ + Add rule    │ + Add rule    │               │
│ ⠿ key_name   │ ⠿ key_name   │ ⠿ key_name    │ ⠿ key_name    │               │
│  fit[Shared] │  fit[Job]    │  fit[Prod]    │  fit[Recr]    │               │
│  [Critical]  │  [High]      │  [Critical]   │  [Critical]   │               │
│  w:100 ⦿[↑][↓]│  w:85 ⦿[↑][↓]│  w:100 ⦿[↑][↓]│  w:100 ⦿[↑][↓]│               │
│  value text  │  value text  │  value text   │  value text   │               │
└──────────────┴──────────────┴───────────────┴───────────────┴───────────────┘
```

Priority badge legend: ≥90 Critical, ≥75 High, ≥50 Med, else Low. Move up/down
sets the rule to `neighbor ± 1` (clamped 0–100); drag redistributes the column.

### Add / Edit Rule Drawer

A right-side drawer (same side as every other drawer), `lg` width.

```text
                     ┌──────────────────────────────────────────────┐
                     │ Add Rule / Edit Rule                [Close] ✕│
                     ├──────────────────────────────────────────────┤
                     │ Scope ▼        Category ▼                    │
                     │ ┌───────────┐  ┌───────────┐                 │
                     │ │ Job ▾     │  │ Fit score ▾│                │
                     │ └───────────┘  └───────────┘                 │
                     │ Key name *      Priority (0-100)             │
                     │ ┌───────────┐  ┌───────────┐                 │
                     │ │ remote_work│  │ 50        │                 │
                     │ └───────────┘  └───────────┘                 │
                     │ Value / rule *                               │
                     │ ┌────────────────────────────────────────┐  │
                     │ │ How the rule matches candidates /       │  │
                     │ │ companies                               │  │
                     │ └────────────────────────────────────────┘  │
                     │ How this affects scoring (optional)          │
                     │ ┌────────────────────────────────────────┐  │
                     │ │ Optional description                   │  │
                     │ └────────────────────────────────────────┘  │
                     │                              [Cancel] [Save] │
                     └──────────────────────────────────────────────┘
```

Full specs: `docs/ux/features/rules/`.

---

### Companies Page

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Companies (128)                       Loaded 25 of 128      Queue           + Add Company│
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Search ............................................        [Industry ▾] [Type ▾] [Status ▾] [Pinned] [Columns] [Clear]│
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ # │ Name │ Industry │ Type │ Location │ Size │ Jobs │ Scores │ Status │ Updated │ Created │
│───┼──────┼──────────┼──────┼──────────┼──────┼──────┼────────┼─────────┼─────────┼─────────│
│ 1 │ Acme │ Software │ Product │ Berlin │ 1-50 │ 12  │ [A+] O 88 S 90 F 85 │ Completed │ 2m │ 2h │
│ 2 │ Acme │ Software │ Product │ Berlin │ —    │ 0   │ [—] O — S — F — │ Completed │ 5m │ 1d │
│ 3 │ Inc  │          │ Unknown │        │      │      │ alias            │           │     │     │
│ 4 │ Beta │ Fintech  │ Consulting │ Munich │ 51-200│ 4 │ [B] O 58 S 55 F 60 │ Completed │ 5m │ 1d │
│   │ Head │ Recruit  │ Recruiting │ Berlin │ 1-50 │ 7¹ │ [—] F — S — O — │ Completed │ 5m │ 1d │
│   │ Nova │ Health   │ Unknown │ —    │ —    │ 0   │ [—] F — S — O — │ Failed   │ 1h │ 2d │
│                                                                                          │
│                                       Loading more companies...                           │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

There is **no dedicated Actions column**. Row actions (Details / Reprocess /
Edit / Delete) are revealed as a floating toolbar at the right edge of the row
on hover (`group-hover`), freeing the column width for the data columns. The
same hover-reveal pattern applies to Jobs and Skills rows.

Alias companies render a small `alias` badge next to their name; selecting the
row opens the detail drawer where the relation can be managed.

The **Jobs** column is adaptive to company role: product companies show the
count of jobs they hire for (`12`), while recruiter-type companies
(`RECRUITING_AGENCY` / `STAFFING_COMPANY`) show the number of jobs they list
for clients (`7¹`, with a `"7 jobs listed for clients"` tooltip). Zero shows
`—`.

A **Type** column (Product / Recruiting Agency / Staffing / Consulting /
Unknown) sits between Industry and Location. Rows are tinted by company type:
**product companies stay white** (no tint, the neutral default) while every
other type gets its **own unique color** (Recruiting Agency = purple, Staffing
= orange, Consulting = teal, Unknown = muted) — a light background that
intensifies on hover/focus. See
`features/companies/company-row.md#company-type-row-colors`.

### Add Company Drawer (Create Entity — company mode)

```text
┌──────────────────────────────────────────────┐
│ + Add Company                          Close │
├──────────────────────────────────────────────┤
│ Primary Link *                               │
│ ┌──────────────────────────────────────────┐ │
│ │ https://acme.example                    │ │
│ └──────────────────────────────────────────┘ │
│ [Website]  [LinkedIn]                        │
│ Company Name (Optional)                      │
│ ┌──────────────────────────────────────────┐ │
│ │ Acme GmbH                               │ │
│ └──────────────────────────────────────────┘ │
│ Additional Links                     [+Add]  │
│   • https://acme.example · careers          │
│ Notes                                 [+Add] │
│   • Berlin product company                  │
├──────────────────────────────────────────────┤
│                [      Add      ] [Add&Process]│
└──────────────────────────────────────────────┘
```

### Company Detail Drawer

```text
┌────────────────────────────────────────────────────────────────┐
│ Company Details                     [Reprocess] [Edit] Close   │
├────────────────────────────────────────────────────────────────┤
│ [A+]  Fit 85 · Success 90 · Overall 88       🔗 Website │
│ ◉ Acme GmbH                                 🔗 Careers │
│ Software Development                        🔗 GitHub  │
│ Berlin, Germany · 51-200 · Product Company                      │
│ 12 jobs                                                        │
│ ◈ Related Companies                                  [ Manage ]│
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ Recommendation: A — apply via careers page                 │ │
│ └────────────────────────────────────────────────────────────┘ │
│ Jobs listed for clients (recruiter-type companies only)         │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ 3 linked jobs                                              │ │
│ │ Senior Backend Engineer                    [B]             │ │
│ │   Berlin · [Fit 84][Success 63][Overall 76]               │ │
│ │ Platform Engineer                          [A]             │ │
│ │   Munich · [Fit 90][Success 70][Overall 82]               │ │
│ │ Data Engineer                             [C]             │ │
│ │   Berlin · [Fit 70][Success 55][Overall 64]               │ │
│ └────────────────────────────────────────────────────────────┘ │
│ Company Overview                                              │
│ Intelligence sections (importance order)                      │
│ Scores explanation (Why popover next to header score cards)   │
│ Linked Jobs                                              │
│ ┌────────────────────────────────────────────────────────┐ │
│ │ 2 linked jobs                                          │ │
│ │ Senior Backend Engineer                    [B]         │ │
│ │   Berlin · [Fit 84][Success 63][Overall 76]           │ │
│ │ Platform Engineer                          [A]         │ │
│ │   Munich · [Fit 90][Success 70][Overall 82]           │ │
│ └────────────────────────────────────────────────────────┘ │
│ Notes & Links (read only)                                     │
└────────────────────────────────────────────────────────────────┘
```

The job-count badge in the header is adaptive like the list's Jobs column:
product companies show `N jobs` (hiring count); recruiter-type companies
(`RECRUITING_AGENCY` / `STAFFING_COMPANY`) show `N listed` (jobs listed for
clients, matching the "Jobs listed for clients" section below).

The link column at the top-right of the score strip lists the company Website
first and the remaining `company.links` beneath it (skipping the link equal to
the website) — mirroring the Job Detail drawer's "Open job posting" link.
Reprocess and Edit live in the drawer header. There is no bottom action footer
— the "View All Jobs" and "Delete" buttons were removed. Deleting a company is
done via the row actions on the Companies page.

### Relate Company Dialog

Opened via `Manage` in the Related Companies section of the Company Detail
drawer. Relating an alias re-points its jobs onto the chosen main.

```text
┌──────────────────────────────────────────────────────────────┐
│ Related Companies                                      Close │
├──────────────────────────────────────────────────────────────┤
│ Relate <current company> to a main company. Jobs linked to   │
│ an alias are re-pointed to the main company.                 │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ [alias of] Acme GmbH                            [Remove] │ │ ← alias only
│ └──────────────────────────────────────────────────────────┘ │
│ Search companies...                                          │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ◉ Acme GmbH                                      2 alias │ │
│ │ ◉ Beta GmbH                                             │ │
│ └──────────────────────────────────────────────────────────┘ │
│                              [Cancel]          [Set as Main] │
└──────────────────────────────────────────────────────────────┘
```

### Processing Drawer (Companies)

The Companies page opens the **shared** Processing Drawer with
`targetType="company"` (same drawer as Jobs, filtered to companies). It is fed
by `GET /api/processing/queue` and live SSE.

```text
┌──────────────────────────────────────────────┐
│ Processing Queue                      Close │
├──────────────────────────────────────────────┤
│ Running (1)                                  │
│ ┌──────────────────────────────────────────┐ │
│ │ Acme GmbH                                │ │
│ │ Step: analyze · ▒▒▒▒░░ 60% · 🗙 Cancel   │ │
│ │ └─ Workflow step tree (live SSE)         │ │
│ └──────────────────────────────────────────┘ │
│ Waiting (2)                                  │
│ ┌──────────────────────────────────────────┐ │
│ │ Beta GmbH                                │ │
│ │ queued · ▶ Start · 🗑 Remove             │ │
│ └──────────────────────────────────────────┘ │
│ Failed (1)                                   │
│ ┌──────────────────────────────────────────┐ │
│ │ Nova                                     │ │
│ │ failed: timeout · ⟳ Retry · 🗑 Remove    │ │
│ └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

The Companies workspace is parity with the Jobs v2 UX (virtualized table,
infinite scroll, Sheet drawers). Company processing runs through the shared
`ProcessingExecution` / SSE lifecycle (context preparation without LLM, then a
single-LLM analysis), monitored via the shared Processing Drawer filtered to
companies. Full specs live in `docs/ux/features/companies/`.

---

### Cities Page

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

The Cities page is the read-only catalog of normalized `{city, country}` rows
produced by the `CityNormalizer` during processing. It mirrors the Companies
v2 list UX: cursor-paginated, infinite scroll, sortable column headers via the
shared `SortableHeader`, debounced search. Jobs column is the default sort
(desc). There is no detail drawer and no row actions — the catalog is derived,
not edited. Full spec lives in `docs/ux/features/cities/page.md`.

---

### Skills Page

The Skills page is parity with the Jobs/Companies v2 UX (virtualized table,
infinite scroll, Sheet drawers). It replaces the legacy SkillsTab. Row actions
(Details / Break down / Merge / Edit / Delete) are revealed on hover as a
floating toolbar at the right edge of the row — there is no fixed Actions column.

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│ </> Skills (128)                     Loaded 25 of 128           + Add Skill   │
├───────────────────────────────────────────────────────────────────────────────┤
│ Search .........................                     [Category ▾] [Pinned] [Columns] │
│ # │ Select │ Name              │ Category   │ Lv │ Roles     │ Demand │ Conf │ Created │
│───│─────── │───────────────────│────────────│────│───────────│────────│──────│─────────│
│ 1 │ ☐      │ Kubernetes 2 aliases│ engineering│ 4  │ DevOps    │ 90%    │ 85%  │ 2m      │
│ 2 │ ☐      │ Kafka             │ technical  │ 2  │ Data      │ 70%    │ 60%  │ 5m      │
│ 3 │ ☐      │ DDD               │ domain     │ 3  │ Backend   │ —      │ 45%  │ 1h      │
│                                                                               │
│                                        Loading more skills...                 │
└───────────────────────────────────────────────────────────────────────────────┘
```

When rows are selected the toolbar shows a bulk action bar:

```text
│ Search .........................                     [Category ▾] [Pinned] [Columns] │
│ 2 selected   [⟳ Merge 2 into...]   [Clear]                                       │
```

The Row number and Select columns are toggled via the Columns dropdown;
merging selected skills into one target reuses the single-merge target picker
dialog. Pinned state is managed from the Skill Detail drawer header, not from
the row. Rows highlight on hover (and while any inner control has focus) with a
muted background and inset ring.
```

### Skill Detail Drawer

```text
┌────────────────────────────────────────────────────────────┐
│ </> Kubernetes (engineering)                       ✕  Edit │
├────────────────────────────────────────────────────────────┤
│ ★ Lv.4   Confidence: 85%   Market: 90%                    │
│ ┌─ Relevant Roles ──────────────────────────────────────┐  │
│ │ DevOps, SRE, Platform                                  │  │
│ └────────────────────────────────────────────────────────┘  │
│ ┌─ Path ────────────────────────────────────────────────┐  │
│ │ Container orchestration → service mesh → ...          │  │
│ └────────────────────────────────────────────────────────┘  │
│ ┌─ Tags ────────────────────────────────────────────────┐  │
│ │ [kubernetes] [helm] [istio]                            │  │
│ └────────────────────────────────────────────────────────┘  │
│ ┌─ Also Known As ───────────────────────────────────────┐  │
│ │ [k8s]                                                  │  │
│ └────────────────────────────────────────────────────────┘  │
│ ┌─ Referenced Jobs (2) ──────────────────────────────────┐  │
│ │ · SRE Engineer        Berlin          [B]             │  │
│ │   Fit 8  Success 7  Overall 9                          │  │
│ │ · Platform Engineer   Munich          [A]             │  │
│ │   Fit 6  Success 8  Overall 7                          │  │
│ │  Click a job → opens it in the Jobs page drawer        │  │
│ └────────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│          [✂ Break down]                    [🗑 Delete]     │
└────────────────────────────────────────────────────────────┘
```

### Add Skill Drawer

```text
┌────────────────────────────────────────────────┐
│ Add Skill                            ✕         │
├────────────────────────────────────────────────┤
│ Name                                        *  │
│ [......................................]      │
│ Level / Category / Relevant Roles / Path      │
│ [Cancel]                          [Add Skill] │
└────────────────────────────────────────────────┘
```

The Skills workspace is parity with the Jobs v2 UX (virtualized table, infinite
scroll, Sheet drawers). Full specs live in `docs/ux/features/skills/` and
`docs/ux/flows/skills/`.

### Candidate Profile Import Page

The Candidate module (110 Phase 1) starts with **Profile Import**: import
resume/LinkedIn sources, run AI analysis, and review the canonical profile.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Candidate Profile                                    [nav: Candidate]    │
├──────────────────────────────────────────────────────────────────────────┤
│ [Sources] [Review]                                                       │
├──────────────────────────────────────────────────────────────────────────┤
│ [SOURCES TAB]                                                            │
│ ┌──────────────────────────┐  ┌──────────────────────────┐              │
│ │ RESUME                   │  │ LINKEDIN                 │              │
│ │ textarea ┌──────────────┐│  │ textarea ┌──────────────┐│              │
│ │          └──────────────┘│  │          └──────────────┘│              │
│ │ [Save Resume]            │  │ [Save Profile]           │              │
│ │ Last updated 5m ago · v2 │  │ Last updated 3d ago · v1 │              │
│ │ [👁 View]                │  │ [👁 View]                │              │
│ └──────────────────────────┘  └──────────────────────────┘              │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ GITHUB (optional — placeholder)    [username..............]        │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ [✨ Analyze Profile]  [☑ Processing]   (queues candidate analysis │  │
│ │  when a resume/LinkedIn is pending; otherwise info toast "no new  │  │
│ │  version"; Processing opens queue drawer for candidate runs)      │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│ [REVIEW TAB]                                                           │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ PROFILE SUMMARY    name · title · version · location               │  │
│ │ [2 skills] [1 experience] [1 project] [1 education] [1 language]   │  │
│ └────────────────────────────────────────────────────────────────────┘  │
│ ┌──────────────────────────┐  ┌──────────────────────────┐              │
│ │ CONNECTED SOURCES        │  │ VERSION HISTORY          │              │
│ │  resume v2 [pending] 5m  │  │  v2 "added linkedin"     │              │
│ │   [👁 View]              │  │  v1 "initial import"     │              │
│ │  linkedin v1 [processed] │  └──────────────────────────┘              │
│ │   3d [👁 View]           │                                           │
│ └──────────────────────────┘                                           │
│ ┌────────────────────────────────────────────────────────────────────┐  │
│ │ SKILLS   [Python L4 96%] [PostgreSQL L4 90%] ...                  │  │
│ ├────────────────────────────────────────────────────────────────────┤  │
│ │ EXPERIENCE  role · company · dates · summary                      │  │
│ ├────────────────────────────────────────────────────────────────────┤  │
│ │ PROJECTS  name · description · url                                 │  │
│ └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

Profile analysis is a background workflow (`CANDIDATE_PROCESSING` execution,
SSE progress); the Review tab refetches `/profile`, `/sources` and `/versions`
after analysis. Analyze only queues a run when a resume/LinkedIn source is still
pending; otherwise it returns `status=noop` and the UI shows an info toast
(persisting a new version requires saving a new source first). Full specs live in
`docs/ux/features/candidate/profile-import.md` and
`docs/ux/flows/candidate/import-profile.md`.

### Job Application Workspace

The Applications module (140) adds a per-job Application Workspace at
`/jobs/{job_id}/application` (entry: airplane action on a job row, or the
**Application** button in the Job Details drawer header). It is a consumer of
existing intelligence — roadmap, tailored resume and cover letter are generated
asynchronously (`roadmap_generation` / `application_resume` /
`application_cover_letter` executions) with SSE progress.

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ ← Back to Job      [Job Detail] [Job Edit] [Open job posting]            │
│ Staff Engineer · Acme GmbH · Berlin                                      │
│ [Recommended] [Apply]       [A+] [Fit 85] [Success 88] [Overall 90] [#3]│
├──────────────────────────────────────────────────────────────────────────┤
│ ▸ AI generation in progress ▸ 42% · "Generating tailored resume"        │  ← SSE card
├──────────────────────────────────────────────────────────────────────────┤
│ APPLICATION                                                            │
│  Status [Recommended ▾]                                                │
│  APPLICATION TIMELINE                                                   │
│  [ Recommended ] [ 2026-08-11 09:00 ▾ ]                          [🗑]   │
│  [ Preparing   ] [ 2026-08-12 14:30 ▾ ]                          [🗑]   │
│  FOLLOW-UPS  ☑ Follow up after interview · Sep 1  [🗑]  [note][📅][Add]  │
├──────────────────────────────────────────────────────────────────────────┤
│ PREPARATION / ROADMAP                                             [⚡ Gen] │
│  No roadmap yet. Generate a job-preparation roadmap             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Kafka → Staff Engineer Roadmap  [ACTIVE]  ▓▓░░ 25%         │ │
│  │ 1/4 tasks done                                             │ │
│  │ MILESTONES · overview (roadmap-application-overview.md)    │ │
│  │ ① Skills foundation [IN PROGRESS][HIGH]  1/2  ▓▓▓▓░        │ │
│  │ ② Ship Kafka project [NOT STARTED][CRIT]  0/2  ░░░░░       │ │
│  │ [View roadmap] [⚡ Regenerate] [🗑 Delete]                  │ │
│  └────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────┤
│ DOCUMENTS                                                               │
│ ┌──────────────────────────┐  ┌──────────────────────────┐              │
│ │ TAILORED RESUME v2       │  │ COVER LETTER v1          │              │
│ │ [👁][copy][↓][✎][🗑][Regen]│  │ [👁][copy][↓][✎][🗑][Regen]│              │
│ └──────────────────────────┘  └──────────────────────────┘              │
└──────────────────────────────────────────────────────────────────────────┘
```

Empty state (no application yet): centered "No application yet" + `[Create Application]`
→ `POST /api/applications` (status `recommended`). The company name in the
header is a **link to the company** (`/companies?company=<id>`) and shows a
company **type badge** next to it when the linked company has a type. Full specs live in
`docs/ux/features/applications/`, `docs/ux/features/roadmaps/` and
`docs/ux/flows/applications/`, `docs/ux/flows/roadmaps/`.

### Placeholders

The Placeholders page (175) stores the user's personal details once so they are
injected into every generated document. Each document card in the workspace has a
**Download PDF** action that fetches a server-rendered PDF with these values filled.

```text
PLACEHOLDERS (/placeholders)
┌──────────────────────────────────────────────────────────┐
│ Placeholders                                             │
│ Personal details injected into generated resumes and     │
│ cover letters. Fill once, then use Download PDF on a     │
│ generated document.                                      │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Your details                                         │ │
│ │ Full name          [ Hassan                 ]        │ │
│ │ Professional title [ Senior Backend Engineer]        │ │
│ │ Email              [ hassan@example.com     ]        │ │
│ │ Phone / Location / LinkedIn / GitHub / Headline ...  │ │
│ │ Professional summary [ 8+ years ...          ]       │ │
│ │                                            [ Save ]  │ │
│ └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘

DOCUMENT CARD (workspace) — Download PDF action
│ [📄] Tailored Resume v2  [👁][copy][↓][PDF][✎][🗑][Regen] │
```

### Roadmaps

The Roadmaps module (144–147) is the replacement for the legacy preparation plan.
A roadmap is a goal + ordered milestones + tasks, either AI-generated from a job
application or created manually. Full specs:
`docs/ux/features/roadmaps/`, `docs/ux/flows/roadmaps/`.

```text
My Roadmaps (/roadmaps)                                    Detail (/roadmaps/{id})
┌─────────────────────────────────────────┐   ┌────────────────────────────────┤
│ My Roadmaps                    [➕ New] │   │ ← My Roadmaps                  │
│ ┌───────────────────┐ ┌──────────────┐ │   │ 🗺 Kafka Roadmap      [Edit]    │
│ │ 🗺 Kafka Roadmap   │ │ 🗺 Career    │ │   │ [APPLICATION][ACTIVE][JOB]      │
│ │ Goal: JOB         │ │ Goal:CUSTOM  │ │   │ Goal: Land a staff role         │
│ │ [APPL][ACTIVE]    │ │ [MAN][ARCH]  │ │   │ ▓▓▓▓▓▓░░░░ 25%  1/4 tasks done  │
│ │ ▓▓▓▓░░ 25%        │ │ ▓▓▓▓▓▓ 50%   │ │   ├────────────────────────────────┤
│ │ [Open][✎][🗑]      │ │ [Open][✎][🗑]│ │   │ JOURNEY              [+ Milestone]│
│ └───────────────────┘ └──────────────┘ │   │ ① Basics ▸ 1/2 · 50%           │
│                                         │   │  ☐ Read docs · MEDIUM          │
│ Empty: 🗺 No roadmaps yet             │   │    NOTES (0)  [Add]             │
│        [+ New Roadmap]                 │   │ ② Apply ▸ 0/3 · 0%             │
└─────────────────────────────────────────┘   └────────────────────────────────┤
```

---

## UX Documentation

Full UX specs live under `docs/ux/` and are split into:

- `docs/ux/design-system/` — reusable primitives (Drawer, ...)
- `docs/ux/features/` — component/page specifications (Jobs page, Add Job, Processing Queue, ...)
- `docs/ux/flows/` — end-to-end user flows (browse, create, process live, ...)

See `docs/ux/README.md` for the full index.
