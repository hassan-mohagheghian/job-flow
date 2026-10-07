"""Opportunity extraction prompt builder — one structured LLM call per message.

``opportunity.extract`` turns a raw inbound message into partial structured
fields. Every field carries an explicit uncertainty state (known / unknown /
inferred / needs_verification); missing information must stay missing, never
be fabricated. The LLM call itself always goes through LLMService (rule #1).
"""

from __future__ import annotations

from typing import Any

OPPORTUNITY_EXTRACT_PROMPT_VERSION = "1.0.0"
OPPORTUNITY_EXTRACT_SCHEMA_VERSION = "1.0.0"


def build_opportunity_extract_output_schema() -> dict[str, Any]:
    """JSON schema for the extraction output."""
    nullable_str = {"type": ["string", "null"]}
    state = {"type": "string", "enum": ["known", "unknown", "inferred", "needs_verification"]}
    return {
        "type": "object",
        "properties": {
            "role_title": nullable_str,
            "role_state": state,
            "company": {
                "type": "object",
                "properties": {
                    "name": nullable_str,
                    "website": nullable_str,
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "state": state,
                },
            },
            "job_urls": {"type": "array", "items": {"type": "string"}},
            "job_description_present": {"type": "boolean"},
            "recruiter": {
                "type": "object",
                "properties": {
                    "name": nullable_str,
                    "email": nullable_str,
                    "state": state,
                },
            },
            "location": {
                "type": "object",
                "properties": {"value": nullable_str, "state": state},
            },
            "work_modes": {"type": "array", "items": {"type": "string"}},
            "employment_types": {"type": "array", "items": {"type": "string"}},
            "salary": nullable_str,
            "skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "level": {"type": ["integer", "null"], "minimum": 0, "maximum": 5},
                        "state": state,
                    },
                    "required": ["name"],
                },
            },
            "experience": nullable_str,
            "sponsorship": {
                "type": "object",
                "properties": {
                    "mentions": {"type": "array", "items": {"type": "string"}},
                    "requires_sponsorship": {"type": ["boolean", "null"]},
                    "state": state,
                },
            },
            "contacts": {"type": "array", "items": {"type": "string"}},
            "application_instructions": nullable_str,
            "uncertainties": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["role_title", "job_urls", "skills", "uncertainties"],
    }


def build_opportunity_extract_prompt(
    source: str,
    sender: str | None,
    subject: str | None,
    raw_content: str,
) -> str:
    """Build the extraction prompt for one inbound message."""
    import json

    schema = json.dumps(build_opportunity_extract_output_schema(), indent=2)
    header = []
    if source:
        header.append(f"SOURCE: {source}")
    if sender:
        header.append(f"SENDER: {sender}")
    if subject:
        header.append(f"SUBJECT: {subject}")
    meta = "\n".join(header)

    return f"""You are parsing an inbound recruiting message for a software engineer seeking a visa-sponsored role in Germany or the Netherlands.

{meta}

MESSAGE:
{raw_content}

Extract whatever information is actually present in the message. Rules:
1. NEVER fabricate missing information. When a field is absent, set its value to null and its state to "unknown".
2. "known": stated explicitly in the message. "inferred": reasonably derived (e.g. a company careers URL implies the company). "needs_verification": plausible but uncertain (e.g. a bare company name with no other evidence). "unknown": absent.
3. job_urls: every URL in the message that looks like a job posting or application link, verbatim. Other URLs (company homepages, LinkedIn profiles) go in contacts, not job_urls.
4. skills: atomic technology names only, lowercase (e.g. "python", not "Python 3.12"). Omit seniority words and non-skills.
5. sponsorship: quote any visa/sponsorship/work-authorization mentions verbatim in mentions; requires_sponsorship is true/false only when the message says so, else null.
6. work_modes: subset of On-site / Remote / Hybrid actually stated. employment_types: subset of Full-time / Part-time / Contract / Internship / Temporary actually stated.
7. uncertainties: short labels for everything important that is still unknown (e.g. "location", "visa sponsorship", "job description").
8. Keep the output short and complete. Respond ONLY with valid JSON matching exactly this schema:

{schema}
"""
