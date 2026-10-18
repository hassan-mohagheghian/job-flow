# Prompt 228 - UX: add-rule affordance when the Rules list is empty

## Objective

When the Rules page has **no rules at all** (or the active filter's scope has none), there is currently *nothing* on screen — no message, no button — so a user cannot create their first rule from the UI. Add a proper empty state with an `Add rule` action that opens the existing Add Rule drawer.

## Current State

- `apps/frontend/src/features/rules/components/RulesTab.tsx`
  - `L201` `filteredScopes = getFilteredScopes().filter(s => scopeGroups[s]?.length > 0)` — scopes with zero rules are dropped, so with `rules = {}` zero `RuleColumn`s render (`L233`).
  - The only `Add rule` button lives **inside** a column (`L122-124`), i.e. it exists only for scopes that already have ≥1 rule.
  - Result with an empty list: header (`L205-210`) + filter tabs with `(0)` counts (`L213-229`) and a blank body.
  - `openAdd(scope)` (`L158-160`) seeds the drawer with `{category:'fit', scope, key:'', value:'', description:'', priority:50}`; `handleAdd` (`L155`) POSTs `/api/rules` — both already work for any scope.
- Backend is complete: `POST /api/rules` exists (`apps/backend/rules/presentation/api/rules_router.py:29-35`), so this is **frontend-only**.
- Docs currently codify the gap: `docs/ux/features/rules/page.md:124-134` — "(no columns render until at least one scope has rules)".
- `Target` is imported in `RulesTab.tsx:2` but unused.

## Implementation Steps

1. `RulesTab.tsx`: when `filteredScopes.length === 0`, render an empty-state panel instead of the columns grid:
   - icon (`Target`), title, one-line explanation, and a primary `Add rule` button.
   - Title/body depend on whether *any* rule exists:
     - `total === 0` → "No scoring rules yet" / explains rules weight job & company scoring.
     - `total > 0` but the filtered scope is empty → "No rules in this scope yet".
   - Button calls `openAdd(filter === 'all' ? 'SHARED' : filter)` so the drawer opens pre-scoped.
   - Filter tabs and header stay visible; nothing else changes.
2. `RuleFormDrawer` untouched — reuses the existing flow (`key={form.id || 'new'}` already handles repeated opens).

## Testing Requirements

`apps/frontend/src/features/rules/components/RulesTab.test.tsx` (extend):

- empty list (`rules={{}}`) → shows the empty state title **and** an `Add rule` button (the existing "renders empty rule columns" test keeps its header assertion).
- clicking that button opens the `Add Rule` drawer (title + key placeholder visible), pre-scoped to `SHARED`.
- filtered scope with no rules (e.g. `Product Company` tab over `mockRules`) → shows "No rules in this scope yet".
- existing non-empty-state tests must stay green (columns, `getAllByText('Add rule')` counts).

Verify with `./scripts/docker-test.sh frontend` plus `npm run lint` and `npm run typecheck` in `apps/frontend` (rule 18: Docker only for tests).

## Docs

- `docs/ux/features/rules/page.md` → replace the Empty State section with the new ASCII wireframe (header, tabs, panel, button) + a small Mermaid state diagram (loading → empty → populated, plus filter-empty branch); update "Available Actions" to mention the empty-state button.
- `docs/ux/README.md` index already lists `rules/page.md` — no new doc file, so no index change.

## Constraints

- AGENTS.md rule 13 (UI change ships with wireframe docs), 18 (tests in Docker), 17 (don't read generated files), 11 (no `print`).
- Frontend stays TypeScript; follow the component's existing conventions (plain `fetch` helper, `cn()`, shadcn/ui `Button`, Phosphor icons, `text-2xs` sizing).
- No backend change, no version bump, no migration.
- Scope confirmed with the user: empty-state affordance only (no persistent header button in this change).
