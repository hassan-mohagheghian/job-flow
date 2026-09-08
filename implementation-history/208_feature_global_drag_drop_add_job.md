# Prompt 208 - Global Drag-and-Drop Job Import (all pages)

## Objective

Dragging a link from another browser tab must open the pre-filled Add Job
drawer from **any page**, not just the Jobs page — so a user can file a new
job wherever they are.

## Current State

- `DropJobOverlay` (`features/jobs-v2/components/DropJobOverlay.tsx`) wraps
  only the Jobs widget (`widgets/jobs-page-v2/index.tsx:176`); other routes
  (`/companies`, `/skills`, `/candidate`, …) have no drop surface.
- The Add Job drawer (`CreateEntityDrawer`, mode `job`) plus its submit flow
  (`useCreateJob` → toast → refetch → optional queue drawer) live inside
  `JobsPage` (`features/jobs-v2/components/JobsPage.tsx:107,236`). The Jobs
  header Add-Job button is its own drop target with `preventDefault` +
  `stopPropagation` (`JobsHeader.tsx:32`).
- Shared URL extraction: `shared/lib/url-drag.ts`
  (`extractUrlFromDataTransfer`, `dataTransferHasUrl`).
- App shell: `apps/frontend/app/layout.tsx` → `Providers`
  (`src/app/providers.tsx`) wraps every route — the global mount point.

## Changes

### Frontend

- New `features/jobs-v2/components/GlobalAddJobProvider.tsx`:
  - Context `{ openAddJobWithUrl(url), openAddJob() }` for programmatic use.
  - Disabled on `/jobs*` routes (`usePathname`): the Jobs page keeps its own
    overlay + drawer, avoiding double overlays / double drawers.
  - Elsewhere: document-level (bubble-phase, so the Jobs header button's
    `preventDefault` wins where present) `dragenter`/`dragover`/`dragleave`/
    `drop` listeners; skip when `e.defaultPrevented`; overlay pill "Drop to
    add job" (same look as `DropJobOverlay`); on drop → pre-filled drawer.
  - Owns `CreateEntityDrawer` (job mode) + `useCreateJob` (duplicate summary +
    "Open application" link preserved) + `JobDetailDrawer` (duplicate "View
    full job details") + `ProcessingDrawer` (opened on Add & Queue).
  - Submit: toast, `queryClient.invalidateQueries({ queryKey: ['jobs'] })`
    (covers `jobs-v2-infinite` and siblings via prefix match), close drawer,
    open queue drawer when queued. Reprocess from detail drawer → `jobApi.
    processJob` + queue drawer.
- `src/app/providers.tsx`: mount `<GlobalAddJobProvider>` inside
  `QueryClientProvider` (needs the query client + auth is irrelevant).
- `GlobalAddJobProvider.test.tsx`: document-level drop opens the drawer
  pre-filled; non-URL drop ignored; no listeners/overlay under `/jobs*`.

### Backend

- None (`POST /api/jobs` + `queue` flag already covers Add / Add & Queue).

## Testing

- New provider test (above); existing `DropJobOverlay` / `JobsHeader` /
  `JobsPage` / `useCreateJob` suites must still pass (Jobs page untouched).
- Typecheck changed files.

## Constraints

- No duplicate drawer on `/jobs*` (route guard is load-bearing).
- Never auto-create/queue on drop — pre-fill only, same as the Jobs flow.
- Docs (rule 13): rewrite `docs/ux/flows/jobs/drag-drop-job.md` for all-pages
  behavior (ASCII + keep Mermaid-less style of that file), touch up
  `docs/ux/features/jobs/add-job.md` trigger table if needed.
