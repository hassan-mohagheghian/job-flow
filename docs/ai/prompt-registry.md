# Prompt Registry

> **Status:** the `PromptRegistry` and the `ai/infrastructure/prompts/`
> package were **removed**; there is no runtime prompt registry anymore.
> The v2 `job.analyze` prompt is self-contained and versioned in
> `processing/application/services/job_analysis_prompt.py`
> (`build_job_analysis_prompt`, `build_job_analysis_output_schema`,
> `JOB_ANALYSIS_PROMPT_VERSION` = "1.6.2", `JOB_ANALYSIS_SCHEMA_VERSION` = "1.1.0").
> It is executed by the `analyze` node of the JobAnalysisGraph via
> `LLMService.generate_structured(prompt, schema=…, timeout=240)` — exactly
> one LLM call per job. The legacy resume/cover letter `.txt` prompt files
> (`resume/step7_cover_generate.txt`, `resume/step_resume_generate.txt`) were
> also removed along with the legacy Socket.IO pipeline — resume/cover letter
> generation is gone from the platform; `jobs/infrastructure/ai/prompts/tailor.py`,
> `cover_letter.py`, `generate_cover_letter.md`, `tailor_resume.md` were removed.

The sections below document the registry design that previously existed.

## Architecture

```
PromptRegistry
├── register(prompt)         — Register a PromptTemplate
├── get(identifier, version) — Get a PromptTemplate by identifier + version
├── render(identifier, ...)  — Shortcut: get + render
├── create_prompt(...)       — Create and register a prompt from a string
├── create_version(...)      — Create a new version of an existing prompt
├── list_identifiers()       — List all registered identifiers
├── list_versions(id)        — List all versions of a prompt
├── list_by_owner(owner)     — List prompts by bounded context
├── list_by_tags(tags)       — List prompts by tags
├── exists(identifier)       — Check if a prompt exists
└── deregister(...)          — Remove a prompt
```

## Module-level convenience functions

```python
from ai.infrastructure.prompts import get_prompt, register_prompt, get_registry

# Quick render
result = get_prompt("job.extract", content="...")

# Quick registration
register_prompt("my.custom", "Template {var}", owner="my-context")

# Access the registry
registry = get_registry()
```

## Registered prompts

| Identifier | Version | Owner | Type | Tags |
|---|---|---|---|---|
| `job.extract` | 1.0.0 | jobs | extraction | job, extraction |
| `job.score` | 1.0.0 | jobs | evaluation | job, scoring |
| `job.summary` | 1.0.0 | jobs | summarization | job, summary |
| `company.extract` | 1.0.0 | companies | extraction | company, extraction |
| `company.analyze` | 1.0.0 | companies | evaluation | company, analysis |
| `resume.tailor` | 1.0.0 | jobs | user | resume, tailoring |
| `resume.cover-letter` | 1.0.0 | jobs | user | resume, cover-letter |
| `skills.extract` | 1.0.0 | skills | extraction | skills, extraction |
| `insights.overview` | 1.0.0 | rules | summarization | rules, insights |
