# Prompt 242 - Make product positioning and AI prompts work-arrangement agnostic

## Objective

Stop positioning the platform around visa-sponsored roles or a specific way of
working (remote / hybrid / on-site). The product must read as a general job
search intelligence tool for any profession and any work arrangement, while the
existing visa and work-type fields stay available as neutral optional metadata.

## Current State

- Positioning copy still singles out visa sponsorship:
  `README.md:3,20,169`, `AGENTS.md:7,10`, `docs/context.md:5,13,20`,
  `docs/ux/features/companies/company-detail.md:10,139`,
  `docs/ux/DESIGN.md:7`.
- AI prompt preambles / instructions assume a visa-seeking candidate:
  `processing/application/services/job_analysis_prompt.py:151,185`,
  `roadmap_generation_prompts.py:74`,
  `application_intelligence_prompts.py:48,78,84`,
  `opportunities/application/services/opportunity_extract_prompt.py:100,114`,
  `opportunity_evaluate_prompt.py:60,74`.
- Prompt versions are pinned in code, tests and docs:
  `JOB_ANALYSIS_PROMPT_VERSION 1.6.1`, `ROADMAP_GENERATION_PROMPT_VERSION 1.0.1`,
  `APPLICATION_INTELLIGENCE_PROMPT_VERSION 1.0.1`,
  `OPPORTUNITY_EXTRACT_PROMPT_VERSION 1.0.1`,
  `OPPORTUNITY_EVALUATE_PROMPT_VERSION 1.0.1`.
- Visa/work-type data plumbing (job fields, filters, company visa analysis,
  opportunity sponsorship extraction, scoring rule) is a real feature and stays
  in place; only its framing changes.

## Changes

1. **Positioning docs** — remove the "visa-sponsored roles" differentiator from
   README, AGENTS.md, docs/context.md and company-detail.md; describe the product
   as profession-, location- and work-arrangement-agnostic. Remove visa/relocation
   wording from illustrative UX examples (`application-tracker.md`,
   `opportunity-detail.md`, `workflow-progress.md`, `jobs/page.md`) but keep the
   factual feature docs for the visa field/filter/company analysis.
2. **AI prompt framing** — address "a professional" instead of "a professional
   seeking a visa-sponsored role"; drop the cover-letter visa/relocation
   instruction; replace "salary/visa notes" and "visa sponsorship" uncertainty
   examples with neutral wording. Keep the `visa` / `work_types` extraction
   fields and opportunity `sponsorship` extraction rules (data contract).
3. **Prompt versions** — patch-bump the content-changed prompts:
   job analysis `1.6.1 → 1.6.2`, roadmap `1.0.1 → 1.0.2`, application
   intelligence `1.0.1 → 1.0.2`, opportunity extract/evaluate `1.0.1 → 1.0.2`.
4. **Tests / docs** — update pinned version assertions in
   `test_job_analysis.py`, `test_roadmap_generation.py`,
   `test_application_intelligence.py`; replace the "visa-sponsored" prompt
   assertions with generic-professional assertions; update version pins in
   `docs/ai/prompts.md`, `docs/ai/prompt-registry.md`,
   `docs/ai/roadmap-generation.md`, `docs/ai/application-intelligence.md`,
   `docs/workflows/job-processing.md`.

## Testing Requirements

- `./scripts/docker-test.sh backend`
- `./scripts/docker-test.sh frontend` (unchanged UI copy, regression only)

## Constraints

- No API, schema, DB or migration change: visa/work-type fields and filters stay.
- Keep the company visa analysis feature; only remove visa-sponsorship as the
  product's positioning and from generic AI role framing.
- Respect AGENTS.md rules 13 (UX docs) and 16 (events untouched).
