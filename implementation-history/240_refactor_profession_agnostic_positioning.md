# Prompt 240 - Make the product positioning and prompts profession-agnostic

## Objective

The platform is usable by any job seeker, not only software engineers. Remove
the "software engineer" assumption from the product positioning, the user-facing
copy, and the AI prompts so a nurse, teacher, marketer or product manager gets
the same quality of analysis, scoring and document generation.

## Current State

- Positioning / audience copy:
  - `README.md:3` and the `For` row at `README.md:33`.
  - `AGENTS.md:7` (project overview).
  - `docs/context.md:5` and the target-user bullets at `docs/context.md:9-11`.
  - `docs/ux/DESIGN.md:5`.
  - `docs/ux/features/companies/company-detail.md:10`.
  - `apps/frontend/app/layout.tsx` metadata description.
- AI prompts hard-code the profession:
  - `processing/application/services/job_analysis_prompt.py:151` plus the
    skill-extraction rules (`SINGLE ATOMIC technology`, engineering-only
    category examples).
  - `candidates/application/services/candidate_extract_prompt.py:156`.
  - `processing/application/services/roadmap_generation_prompts.py:74`.
  - `processing/application/services/application_intelligence_prompts.py:48,78`
    and the "technology/culture" wording at `:51,83`.
  - `opportunities/application/services/opportunity_extract_prompt.py:100,111`.
  - `opportunities/application/services/opportunity_evaluate_prompt.py:60`.
  - `companies/infrastructure/ai/prompts/company{,_combined}_analyze.txt:1` and
    the fit bands at the bottom (`Python/Django/FastAPI/PG/K8s`).
  - `companies/infrastructure/ai/prompts/company{,_combined}_extract.txt:114`
    ("connecting engineers with companies").
- Title-specific UI placeholders:
  - `shared/components/CreateEntityDrawer.tsx:479`,
    `features/jobs-v2/components/JobEditDrawer.tsx:202,214`,
    `features/roadmaps/components/RoadmapCreateDialog.tsx:69,88`,
    `features/skills-v2/components/AddSkillDrawer.tsx:155`.
- Prompt versions are pinned in tests and docs:
  `test_job_analysis.py:465,765`, `test_roadmap_generation.py:379-380`,
  `test_application_intelligence.py:341`, `docs/ai/prompts.md`,
  `docs/ai/prompt-registry.md`, `docs/ai/application-intelligence.md`,
  `docs/ai/roadmap-generation.md`, `docs/workflows/job-processing.md`.

## Changes

1. **Positioning copy** — describe the audience as job seekers in any
   profession (visa-sponsored roles stay the differentiator):
   `README.md`, `AGENTS.md`, `docs/context.md` (overview, target users, plus an
   explicit "profession-agnostic" statement), `docs/ux/DESIGN.md`,
   `docs/ux/features/companies/company-detail.md`, `app/layout.tsx` metadata.
2. **AI prompts** — address "a professional" / "the candidate" instead of a
   software engineer; replace engineering-only examples with field-neutral ones
   (`technology` → `skill or tool`, generic skill categories); drop hard-coded
   `Europe` / `Germany or the Netherlands` from prompts that are meant to be
   location-agnostic. Company prompts: generalize the fit measures and scoring
   bands so they reward alignment with the candidate's own field, skills and
   goals instead of a fixed Python stack. JSON keys stay unchanged (data
   contract).
3. **Prompt versions** — patch-bump the affected constants (content change,
   schema unchanged): job analysis `1.6.0 → 1.6.1`, candidate extract
   `1.0.0 → 1.0.1`, roadmap `1.0.0 → 1.0.1`, application intelligence
   `1.0.0 → 1.0.1`, company analysis `1.2.0 → 1.2.1`, opportunity extract /
   evaluate `1.0.0 → 1.0.1`. Update the pinned tests and the docs above.
4. **UI placeholders** — use cross-profession examples in the job title, role,
   relevant-roles and roadmap fields; update
   `docs/ux/features/jobs/add-job.md` examples and add a profession-agnostic
   copy convention to `docs/ux/DESIGN.md`.
5. **Tests** — update `CreateEntityDrawer.test.tsx` to the new title
   placeholder and the pinned prompt-version assertions.

## Testing Requirements

- `./scripts/docker-test.sh backend` (prompt/version tests).
- `./scripts/docker-test.sh frontend`, then `npm run lint` and
  `npm run typecheck` in `apps/frontend`.
- `grep -rniE "software engineer" README.md AGENTS.md docs/context.md
  docs/ux/DESIGN.md` returns no product-positioning matches.

## Constraints

- No behavior, API, schema or migration change: prompt JSON keys, response
  shapes and the skills taxonomy stay untouched.
- Keep "visa-sponsored roles" as the product differentiator.
- Do not rewrite illustrative example data in wireframes, API examples, tests
  or `data/plan/` — examples are data, not positioning.
- Do not add engineering-specific requirements for new users.
