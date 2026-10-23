# Prompt 241 - Widen the page content area and the jobs timeline

## Objective

Give the data-heavy pages (Dashboard, Jobs, Opportunities, Companies, Cities,
Skills) almost the full window width — only a small horizontal gutter — and widen
the Jobs "Jobs added" timeline so its month/day/apply content has room to breathe.

## Current State

- `apps/frontend/src/widgets/sidebar/index.tsx:309-313` — the page `<main>` uses
  `p-4` and its inner wrapper caps content at `max-w-[1400px] mx-auto`, leaving
  large empty margins on wide monitors.
- `apps/frontend/src/features/jobs-v2/components/JobTimeline.tsx:45` — the
  timeline `<aside>` is a fixed `w-24` (~96px) column with `px-2` rows.
- Page widgets (`JobsPage`, `CompaniesPage`, `CitiesPage`, `SkillsPage`,
  `OpportunitiesPage`, `DashboardPage`) all render inside that shell container
  and fill `h-full`, so the shell is the single place to widen them.
- Docs: `docs/ux/app-shell.md:171-172` (page content sizing),
  `docs/ux/features/jobs/job-created-timeline.md:34` (explicit ~96px width),
  `docs/ux/DESIGN.md:94` (timeline description).

## Changes

1. **App shell** — in `widgets/sidebar/index.tsx`, change the `<main>` gutter
   from `p-4` to `px-2 py-3 lg:px-3` (8px mobile / 12px desktop horizontal
   margin) and replace the `max-w-[1400px] mx-auto` wrapper with
   `h-full w-full`. Add `data-testid="page-content"` on the inner wrapper for
   regression tests.
2. **Timeline** — in `features/jobs-v2/components/JobTimeline.tsx`, widen the
   `<aside>` from `w-24` to responsive `w-40 xl:w-48` (160px → 192px), and bump
   header/row padding from `px-2` to `px-3` so the extra width is used.
3. **Tests** — extend `widgets/sidebar/Sidebar.test.tsx` with a content-width
   assertion (small horizontal padding, no 1400px cap) and
   `features/jobs-v2/components/JobTimeline.test.tsx` with a width assertion.
4. **Docs** — update `docs/ux/app-shell.md`, `docs/ux/DESIGN.md`,
   `docs/ux/features/jobs/job-created-timeline.md`, and add the shared
   content-width convention line to the Dashboard, Jobs, Opportunities,
   Companies, Cities and Skills page docs.

## Testing Requirements

- `./scripts/docker-test.sh frontend`
- `cd apps/frontend && npm run lint && npm run typecheck`

## Constraints

- No backend, API, data or behavior change — layout only.
- Keep the existing page semantics and scroll behavior (`main` remains the page
  scroll container; widgets stay `h-full`).
- Respect AGENTS.md rule 13 (UX docs + wireframes stay in sync).
