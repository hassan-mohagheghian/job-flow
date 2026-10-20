# Prompt 235 - Fix job analysis losing title, company and location

## Objective

Recent job processing persists jobs with empty `title`, `company` and
`location` even though the LLM read the posting. Repair the LLM output handling
so schema-shaped responses are unwrapped and degraded analyses are retried
instead of silently saved.

## Current State

- `apps/backend/processing/application/services/job_analysis_prompt.py` embeds
  the full output schema in the prompt (prompt version `1.5.0`) and the
  opencode provider appends the same schema again.
- `apps/backend/ai/infrastructure/providers/opencode/adapter.py`
  (`generate_structured`) only checks that the response parses as JSON.
- Models frequently answer with
  `{"type": "object", "properties": {<real fields>}, "scores": {...}}`.
  `JobAnalysisOutput` ignores the unknown `type`/`properties` keys, so the
  top-level `title`/`company`/`location`/`description` default to `None` and
  the degraded payload validates and is persisted.
- `apps/backend/processing/application/workflows/job_analysis/nodes/analyze_node.py`
  accepts such a payload because the required keys (`scores`, `recommendation`,
  `summary`, `skills`, `insights`) are present.
- Confirmed on job `01a1599b-4e69-7495-bc93-357844d3dcc6`
  (`https://remoteyeah.com/jobs/remote-developer-advocate-serpapi`).

## Changes

1. `apps/backend/ai/infrastructure/parsers.py`: add
   `unwrap_schema_echo(payload)` — when a response is a schema-shaped wrapper
   (`type == "object"` + a `properties` dict holding data values), merge the
   properties with the sibling keys and drop `type`/`properties`/`required`.
   Pure schema definitions (every property is a `{"type": ...}` node) are left
   untouched so validation can reject them.
2. `apps/backend/ai/infrastructure/providers/opencode/adapter.py`:
   - apply `unwrap_schema_echo` to the parsed JSON in `generate_structured`;
   - stop appending the schema when the prompt already contains it;
   - append an explicit "return the data object, never the schema wrapper"
     instruction.
3. `apps/backend/processing/application/workflows/job_analysis/nodes/analyze_node.py`:
   - unwrap schema echoes before validation (defense in depth);
   - reject payloads whose `title`, `company`, `location`, `role` and
     `description` are all empty, so the node retries;
   - extend `_RETRY_SHORTEN_HINT` with the missing-field and no-schema-wrapper
     requirements.
4. `apps/backend/processing/application/services/job_analysis_prompt.py`: add
   the no-schema-wrapper output rule and bump `JOB_ANALYSIS_PROMPT_VERSION` to
   `1.6.0` (schema unchanged at `1.1.0`).
5. Docs: update `docs/ai/prompts.md` and `docs/workflows/job-processing.md`
   version references and document the schema-echo repair behavior.

## Testing Requirements

- `apps/backend/tests/ai/infrastructure/providers/opencode/test_opencode_adapter.py`:
  unwrap wrapper responses, leave plain responses untouched, do not duplicate
  the schema when the prompt already embeds it.
- `apps/backend/tests/processing/application/test_job_analysis.py`: schema
  echo payload fills title/company/location; all-empty extraction triggers a
  retry; prompt contains the no-schema-wrapper rule; bump version assertions.
- Run `./scripts/docker-test.sh backend`.

## Constraints

- Respect AGENTS.md rules 1 (LLMService), 3 (typed frontend), 12/versioning and
  18 (Docker tests).
- No behavior change for callers that already send plain JSON.
- Keep the public output schema (`JOB_ANALYSIS_SCHEMA_VERSION`) unchanged.
