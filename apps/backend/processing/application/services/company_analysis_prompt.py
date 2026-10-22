"""Company analysis prompt builder — a single combined LLM call for a company.

The Company Analysis workflow performs exactly one LLM call per company
(company.analyze_company). This module owns the prompt (versioned), loads the
combined template from the Companies bounded context, and appends the JSON
output schema. The LLM call itself always goes through LLMService (AGENTS.md
rule #1).
"""

from __future__ import annotations

import json
from typing import Any

from shared.infrastructure.prompts.loader import load_prompt

COMPANY_ANALYSIS_PROMPT_VERSION = "1.2.1"
COMPANY_ANALYSIS_SCHEMA_VERSION = "1.2.0"

_COMBINED_PROMPT_NAME = "company/company_combined_analyze"


def build_company_analysis_output_schema() -> dict[str, Any]:
    """JSON schema for the combined analysis output."""
    nullable_str = {"type": ["string", "null"]}
    string_list = {"type": "array", "items": {"type": "string"}}
    nullable_string_list = {"type": ["array", "null"], "items": {"type": "string"}}
    object_field = {"type": "object", "additionalProperties": True}
    nullable_object = {"type": ["object", "null"], "additionalProperties": True}

    return {
        "type": "object",
        "properties": {
            "extraction": {
                "type": "object",
                "properties": {
                    "name": nullable_str,
                    "website": nullable_str,
                    "domain": nullable_str,
                    "industry": nullable_str,
                    "country": nullable_str,
                    "city": nullable_str,
                    "description": nullable_str,
                    "company_size": nullable_str,
                    "company_type": nullable_str,
                    "logo_url": nullable_str,
                    "founded_year": nullable_str,
                    "headquarters_full": nullable_str,
                    "countries_of_operation": nullable_string_list,
                    "products": nullable_string_list,
                    "tech_stack": nullable_object,
                    "work_environment": nullable_object,
                    "funding_stage": nullable_str,
                    "funding_amount": nullable_str,
                    "skills": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "category": {"type": "string"},
                                "evidence": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                },
            },
            "intelligence": {
                "type": "object",
                "properties": {
                    "overview": object_field,
                    "culture_analysis": object_field,
                    "international_analysis": object_field,
                    "career_analysis": object_field,
                    "benefits_analysis": object_field,
                    "visa_analysis": object_field,
                    "technology_analysis": object_field,
                },
            },
            "recommendation": {
                "type": "object",
                "properties": {
                    "priority": nullable_str,
                    "observation": nullable_str,
                    "evidence": nullable_str,
                    "impact": nullable_str,
                    "action": nullable_str,
                    "ideal_role": nullable_str,
                    "timing": nullable_str,
                },
            },
            "scores": {
                "type": "object",
                "properties": {
                    "fit": {"type": "integer", "minimum": 0, "maximum": 100},
                    "success": {"type": "integer", "minimum": 0, "maximum": 100},
                    "overall": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
                    "fit_grade": nullable_str,
                    "fit_explanation": nullable_str,
                    "fit_positive_factors": string_list,
                    "fit_negative_factors": string_list,
                    "success_explanation": nullable_str,
                    "success_positive_factors": string_list,
                    "success_negative_factors": string_list,
                    "overall_grade": nullable_str,
                },
            },
        },
        "required": ["extraction", "scores"],
    }


def build_company_analysis_prompt(
    company_content: str,
    company_type: str,
    rules: str,
    input_type: str = "url",
    resume_text: str = "",
    profile_documents: str = "",
    target_countries: str = "your target countries",
) -> str:
    """Build the single combined analysis prompt for a company.

    resume_text and profile_documents carry the candidate's latest resume and
    LinkedIn profile (and structured candidate profile when available) as labeled
    extra context, mirroring the job analysis prompt. The resume is authoritative
    for skills/seniority; LinkedIn supplements it.
    """
    template = load_prompt(
        _COMBINED_PROMPT_NAME,
        company_content=company_content,
        input_type=input_type,
        company_type=company_type,
        rules=rules,
        resume_text=resume_text,
        profile_documents=profile_documents,
        target_countries=target_countries,
    )
    schema = json.dumps(build_company_analysis_output_schema(), indent=2)
    return f"""{template}

RESPOND ONLY with valid JSON matching exactly this schema:

{schema}
"""
