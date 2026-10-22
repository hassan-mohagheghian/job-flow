"""candidate.extract prompt builder — a single structured LLM call per source.

The Candidate Profile workflow performs one LLM call per source document. This
module owns that prompt (versioned) and its output JSON schema. The LLM call
itself always goes through LLMService (AGENTS.md rule #1).
"""

from __future__ import annotations

import json
from typing import Any

CANDIDATE_EXTRACT_PROMPT_VERSION = "1.0.1"
CANDIDATE_EXTRACT_SCHEMA_VERSION = "1.0.0"

PROFICIENCY_VALUES = ("basic", "conversational", "professional", "fluent", "native")


def _confidence_field() -> dict[str, Any]:
    return {"type": "number", "minimum": 0.0, "maximum": 1.0}


def _skill_item() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "level": {"type": "integer", "minimum": 0, "maximum": 5},
            "category": {"type": "string"},
            "years_of_experience": {"type": ["number", "null"]},
            "last_used": {"type": ["string", "null"]},
            "confidence": _confidence_field(),
        },
        "required": ["name"],
    }


def _experience_item() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "company": {"type": "string"},
            "role": {"type": "string"},
            "start_date": {"type": ["string", "null"]},
            "end_date": {"type": ["string", "null"]},
            "duration_months": {"type": ["integer", "null"]},
            "summary": {"type": "string"},
            "highlights": {"type": "array", "items": {"type": "string"}},
            "skills": {"type": "array", "items": {"type": "string"}},
            "confidence": _confidence_field(),
        },
        "required": ["company", "role"],
    }


def _project_item() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "url": {"type": "string"},
            "role": {"type": "string"},
            "skills": {"type": "array", "items": {"type": "string"}},
            "start_date": {"type": ["string", "null"]},
            "end_date": {"type": ["string", "null"]},
            "confidence": _confidence_field(),
        },
        "required": ["name"],
    }


def _education_item() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "institution": {"type": "string"},
            "degree": {"type": "string"},
            "field": {"type": "string"},
            "start_date": {"type": ["string", "null"]},
            "end_date": {"type": ["string", "null"]},
            "confidence": _confidence_field(),
        },
        "required": ["institution"],
    }


def _certificate_item() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "issuer": {"type": "string"},
            "issue_date": {"type": ["string", "null"]},
            "credential_url": {"type": "string"},
            "confidence": _confidence_field(),
        },
        "required": ["name"],
    }


def _interest_item() -> dict[str, Any]:
    return {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}


def _language_item() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "proficiency": {"type": "string", "enum": list(PROFICIENCY_VALUES)},
        },
        "required": ["name"],
    }


def build_candidate_extract_output_schema() -> dict[str, Any]:
    """JSON schema for the structured candidate profile extraction output."""
    return {
        "type": "object",
        "properties": {
            "profile": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "title": {"type": "string"},
                    "headline": {"type": "string"},
                    "summary": {"type": "string"},
                    "location": {"type": "string"},
                },
            },
            "skills": {"type": "array", "items": _skill_item()},
            "experiences": {"type": "array", "items": _experience_item()},
            "projects": {"type": "array", "items": _project_item()},
            "educations": {"type": "array", "items": _education_item()},
            "certificates": {"type": "array", "items": _certificate_item()},
            "interests": {"type": "array", "items": _interest_item()},
            "languages": {"type": "array", "items": _language_item()},
        },
        "required": [
            "profile",
            "skills",
            "experiences",
            "projects",
            "educations",
            "certificates",
            "interests",
            "languages",
        ],
    }


def build_candidate_extract_prompt(source_type: str, raw_text: str) -> str:
    """Build the structured extraction prompt for a single source document."""
    schema = json.dumps(build_candidate_extract_output_schema(), indent=2)
    return f"""You are a career intelligence engine. Extract the COMPLETE factual profile of a professional from the raw {source_type.upper()} document below.

Extract ONLY facts that are actually present in the document. Do not invent, guess, or fill gaps from general knowledge. When a fact is absent, omit it (null / empty string / empty array as appropriate).

PROFILE:
  name: the person's full name (or empty).
  title: their most recent job title.
  headline: their stated headline / tagline (e.g. from LinkedIn), if present.
  summary: a concise 1-2 sentence professional summary drawn from the document (at most 80 words).
  location: their location / city, if present.

SKILLS:
  List every skill mentioned (skills, tools, domains, certifications, methods). One entry per skill name.
  level: an estimate of proficiency 1-5 based on the document (5 = expert, daily use for years).
  category: a coarse category that fits the person's profession (e.g. skill, tool, domain, certification, language, method). Empty when unclear.
  years_of_experience: number of years evidenced in the document, or null.
  last_used: the last year/context the skill appears, or null.
  confidence: how certain you are this skill belongs to the person (0.0-1.0). Default 0.8 when stated, 0.5 when only implied.

EXPERIENCES:
  One entry per job/role. company, role, start_date / end_date (year or year-month, as given; null when absent), duration_months (derive from dates when possible, else null), summary (at most 60 words), highlights (short bullets), skills (skills used in that role), confidence.

PROJECTS:
  Personal / open-source / notable projects: name, description (at most 50 words), url, role, skills, start_date, end_date, confidence.

EDUCATIONS:
  institution, degree, field, start_date, end_date, confidence.

CERTIFICATES:
  name, issuer, issue_date, credential_url, confidence.

INTERESTS:
  Stated interests/hobbies as a list of names.

LANGUAGES:
  Spoken languages with proficiency one of: basic, conversational, professional, fluent, native.

OUTPUT SIZE LIMITS (critical — never truncate the JSON):
 1. summary: at most 80 words. experience summary: at most 60 words. project description: at most 50 words.
 2. skills: at most 40 entries. experiences/projects/educations: as many as appear (usually under 15).
 3. The JSON must be complete and valid — every string and bracket closed.

RAW {source_type.upper()} DOCUMENT:
{raw_text}

Respond ONLY with valid JSON matching exactly this schema:

{schema}
"""
