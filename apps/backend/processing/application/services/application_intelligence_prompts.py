"""Application Intelligence prompt builders — tailored resume and cover letter
generation.

Each builder produces a versioned prompt plus its strict output JSON schema.
The LLM call always goes through LLMService (AGENTS.md rule #1) and the result
is validated against the mirrored Pydantic models in
``application_intelligence_validation``.

These generators are *consumers* of existing Career Intelligence: the prompt is
grounded in the persisted job analysis, company intelligence and candidate
profile. They never re-analyze the job, company or user.
"""

from __future__ import annotations

import json
from typing import Any

APPLICATION_INTELLIGENCE_PROMPT_VERSION = "1.0.1"
APPLICATION_INTELLIGENCE_SCHEMA_VERSION = "1.0.0"

# Literal contact placeholder tokens the LLM is told to emit (not an f-string).
CONTACT_PLACEHOLDERS = "{{name}}, {{title}}, {{email}}, {{phone}}, {{location}}, {{linkedin}}, {{github}}"


def build_document_output_schema() -> dict[str, Any]:
    """JSON schema for generated documents (tailored resume / cover letter).

    Documents are plain markdown content inside an envelope so the response is
    parseable and the content is directly editable in the workspace.
    """
    return {
        "type": "object",
        "properties": {
            "content": {"type": "string"},
        },
        "required": ["content"],
    }


def _sections(context: dict[str, str], keys: list[str]) -> str:
    return "\n\n".join(context.get(k) or f"{k.upper()}:\n  (no data available)" for k in keys)


def build_resume_prompt(context: dict[str, str]) -> str:
    """Build the tailored resume prompt (grounded in job + company + candidate)."""
    schema = json.dumps(build_document_output_schema(), indent=2)
    return f"""You are a senior career advisor writing a tailored resume for a professional applying for a visa-sponsored role.

Write a complete, professional resume as MARKDOWN (not JSON) that:
1. Is tailored to THIS job posting and THIS company — mirror the job's required skills and the company's field and culture signals.
2. Uses ONLY facts from the candidate profile below. Never invent experience, skills, employers or dates.
3. Emphasizes the candidate's matched skills and achievements that map to the job's required skills (from the job analysis).
4. Ordering: contact/header → professional summary (2-3 lines) → core competencies (skills relevant to the job) → experience (reverse chronological) → projects → education → certificates → languages.
5. Uses markdown headings (##), bullet lists, and bold for job titles / company names.

{_sections(context, ["job", "company", "candidate"])}

PLACEHOLDERS:
- In the contact/header block ONLY, use placeholder tokens for the candidate's personal details exactly as: {CONTACT_PLACEHOLDERS}.
- The user fills these values on the Placeholders page before download — never hardcode a personal detail you are not certain about; keep the token so it can be filled.
- Do NOT use placeholder tokens anywhere else (skills, experience, projects stay concrete from the profile).

CONSTRAINTS:
- Output ONLY the resume markdown content inside the JSON envelope "content". No preamble, no code fences.
- Keep the resume to at most one page of focused content — every bullet must be high-signal for this specific application.
- Do not add placeholder sections the candidate has no data for.

Respond ONLY with valid JSON matching exactly this schema:

{schema}
"""


def build_cover_letter_prompt(context: dict[str, str]) -> str:
    """Build the cover letter prompt (grounded in job + company + candidate)."""
    schema = json.dumps(build_document_output_schema(), indent=2)
    return f"""You are a senior career advisor writing a cover letter for a professional applying for a visa-sponsored role.

Write a complete, professional cover letter as MARKDOWN (not JSON) that:
1. Opens with a clear subject line (## Subject) and a formal greeting addressed to the hiring team.
2. States the role, company and how the candidate found it.
3. In 3-5 body paragraphs, connects the candidate's real experience (from the profile ONLY) to the job's required skills and the company's field and culture (from the intelligence below). Show, don't tell — use concrete achievements from the profile.
4. Explicitly addresses the visa/relocation angle briefly and confidently (the candidate is seeking a visa-sponsored role).
5. Closes with a call to action and a professional signature (## Signature).

{_sections(context, ["job", "company", "candidate"])}

PLACEHOLDERS:
- In the signature block ONLY, use placeholder tokens for the candidate's personal details exactly as: {CONTACT_PLACEHOLDERS}.
- The user fills these values on the Placeholders page before download — never hardcode a personal detail you are not certain about; keep the token so it can be filled.
- Do NOT use placeholder tokens anywhere else in the body.

CONSTRAINTS:
- Output ONLY the cover letter markdown content inside the JSON envelope "content". No preamble, no code fences.
- Keep the letter to at most 350 words.
- Never invent experience, numbers, or facts not present in the candidate profile.

Respond ONLY with valid JSON matching exactly this schema:

{schema}
"""
