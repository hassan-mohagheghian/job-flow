"""Opportunity evaluation prompt builder — one structured LLM call per evaluation.

``opportunity.evaluate`` scores an extracted opportunity against the candidate
profile, the enabled scoring rules, and the linked job/company summaries. The
LLM provides fit/success numbers plus explanatory dimensions; deterministic
post-processing (overall, recommendation, application path) happens in
OpportunityService and reuses the job-scoring helpers. The LLM call itself
always goes through LLMService (rule #1).
"""

from __future__ import annotations

import json
from typing import Any

OPPORTUNITY_EVALUATE_PROMPT_VERSION = "1.0.0"
OPPORTUNITY_EVALUATE_SCHEMA_VERSION = "1.0.0"


def build_opportunity_evaluate_output_schema() -> dict[str, Any]:
    """JSON schema for the evaluation output."""
    nullable_str = {"type": ["string", "null"]}
    return {
        "type": "object",
        "properties": {
            "fit": {"type": "integer", "minimum": 0, "maximum": 100},
            "success": {"type": "integer", "minimum": 0, "maximum": 100},
            "technical_match": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
            "experience_match": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
            "location_match": {"type": "string", "enum": ["match", "partial", "mismatch", "unknown"]},
            "seniority_match": {"type": "string", "enum": ["match", "partial", "mismatch", "unknown"]},
            "employment_match": {"type": "string", "enum": ["match", "partial", "mismatch", "unknown"]},
            "salary_match": {"type": "string", "enum": ["match", "partial", "mismatch", "unknown"]},
            "authorization": nullable_str,
            "career_alignment": {"type": ["integer", "null"], "minimum": 0, "maximum": 100},
            "concerns": {"type": "array", "items": {"type": "string"}},
            "missing_requirements": {"type": "array", "items": {"type": "string"}},
            "unknown_information": {"type": "array", "items": {"type": "string"}},
            "enough_to_apply": {"type": "boolean"},
            "recommended_next_action": nullable_str,
        },
        "required": ["fit", "success", "concerns", "missing_requirements", "unknown_information", "enough_to_apply"],
    }


def build_opportunity_evaluate_prompt(
    extracted_summary: str,
    candidate_profile_text: str,
    scoring_rules: str,
    linked_job_summary: str = "",
    linked_company_summary: str = "",
) -> str:
    """Build the evaluation prompt for one extracted opportunity."""
    schema = json.dumps(build_opportunity_evaluate_output_schema(), indent=2)
    linked = ""
    if linked_job_summary:
        linked += f"\nLINKED JOB (existing record):\n{linked_job_summary}\n"
    if linked_company_summary:
        linked += f"\nLINKED COMPANY (existing record):\n{linked_company_summary}\n"
    return f"""You are a senior career advisor for a software engineer seeking a visa-sponsored role in Germany or the Netherlands.

Evaluate the inbound opportunity below against the candidate profile and the scoring rules.

EXTRACTED OPPORTUNITY (fields marked unknown/inferred/needs_verification are uncertain — treat them as such):
{extracted_summary}
{linked}
CANDIDATE PROFILE (canonical — the source of truth):
{candidate_profile_text}

SCORING RULES TO APPLY:
{scoring_rules}

Your evaluation must:
1. Score fit (0-100): how well the opportunity matches the profile (skills, seniority, domain). Only use information actually present; uncertainty lowers confidence, never raises scores.
2. Score success (0-100): the probability of an offer (seniority match, competition, authorization outlook).
3. Explain with concrete factors; list concerns (gaps, mismatches, risks) — at most 3.
4. List missing requirements and unknown information explicitly (at most 5 each). Do not invent values to fill them.
5. Set enough_to_apply only when the candidate could act now (a reachable path plus sufficient facts).
6. Suggest one concrete recommended_next_action grounded in the available information (e.g. ask the recruiter for the JD, clarify location/work authorization, apply via the posting).

Respond ONLY with valid JSON matching exactly this schema:

{schema}
"""
