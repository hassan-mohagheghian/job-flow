# Prompt 233 - Abstract location wording in the README and overview docs

## Objective

Remove geography from the project's positioning: the platform is described
generically (visa-sponsored roles), not as a Germany/Netherlands or
city-specific product.

## Current State

- `README.md:3` — "Built for visa-sponsored roles in Europe (Germany, Netherlands)."
- `docs/context.md:5` — "…especially visa-sponsored roles in Europe (Germany, Netherlands)."
- `docs/context.md:9` — "Software engineers seeking visa-sponsored positions in Europe"
- `AGENTS.md:7` — "…seeking visa-sponsored roles in Europe (Germany, Netherlands)."

## Changes

1. `README.md` — drop the region/country clause: "Built for visa-sponsored roles."
2. `docs/context.md` — drop "in Europe (Germany, Netherlands)" from the overview
   and "in Europe" from the target-users bullet.
3. `AGENTS.md` — drop "in Europe (Germany, Netherlands)" from the project
   overview.

Examples in API docs, UX wireframes, and the cities feature docs are left
untouched — they are illustrative data, not product positioning.

## Testing Requirements

- Docs-only change; no code or tests affected.
- `grep -niE "europe|germany|netherlands" README.md docs/context.md AGENTS.md`
  returns no matches.

## Constraints

- Do not change product behavior, API examples, or UX wireframes.
- Keep "visa-sponsored roles" as the product's differentiator.
