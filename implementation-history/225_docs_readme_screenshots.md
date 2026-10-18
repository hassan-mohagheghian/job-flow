# Prompt 225 - Add System Screenshots to the Root README

## Objective
Showcase the product's key screens in the root `README.md` using the screenshots the user supplied, and relocate those images from the ad-hoc root `assets/` folder into the repository's documentation tree.

## Current State
- `README.md` (root) has no images — no `![...]` references anywhere in the repo (grep confirmed).
- Untracked `assets/` at repo root holds three PNGs (826×765, RGBA): `dashboard.png`, `job-list.png`, `job-processing.png`. Folder is not referenced by any doc.
- Documentation lives under `docs/` (see `docs/ux/`, `docs/architecture/`, ...); there was no `docs/assets/` directory.
- `docs/ux/features/dashboard/` exists (rule 13 docs already present for the dashboard UI).

## Changes
1. Create `docs/assets/` and move the three PNGs there (`dashboard.png`, `job-list.png`, `job-processing.png`); remove the now-empty root `assets/` folder.
2. `README.md`: add a `## Screenshots` section after the intro line and before `## Quick Start`:
   - Dashboard + Jobs side by side in a 2-column Markdown table with descriptive alt text.
   - Job Processing as a full-width image with a one-line caption describing the live pipeline.
   - Image paths are relative to the repo root: `docs/assets/<name>.png`.

## Testing Requirements
- No code tests apply (docs-only change).
- Verify each referenced path exists: `docs/assets/dashboard.png`, `docs/assets/job-list.png`, `docs/assets/job-processing.png`.
- Confirm Markdown renders (images resolve from the repo root) and the old `assets/` no longer exists.

## Constraints
- Docs-only; no backend/frontend behavior changes.
- Respect AGENTS.md: keep asset paths relative to the README location; do not add generated/cache files.
- Do not modify UI, so no new wireframe docs are required (AGENTS.md rule 13 covers UI changes).
