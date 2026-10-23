"""Job analysis prompt builder — a single combined LLM call for a job.

The Job Analysis workflow performs exactly one LLM call per job. This module
owns that prompt (versioned) and its output JSON schema. The LLM call itself
always goes through LLMService (AGENTS.md rule #1).
"""

from __future__ import annotations

import json
from typing import Any

JOB_ANALYSIS_PROMPT_VERSION = "1.6.2"
JOB_ANALYSIS_SCHEMA_VERSION = "1.1.0"

COMPANY_TYPE_VALUES = [
    "hiring",
    "recruiter",
    "staffing",
    "consulting",
    "outsourcing",
    "unknown",
]


def build_company_reference_schema() -> dict[str, Any]:
    """JSON schema for a single extracted company reference."""
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "normalized_name": {"type": "string"},
            "company_type": {"type": "string", "enum": COMPANY_TYPE_VALUES},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reason": {"type": "string"},
        },
        "required": ["name"],
    }


def build_job_analysis_output_schema() -> dict[str, Any]:
    """JSON schema for the combined analysis output."""
    nullable_str = {"type": ["string", "null"]}
    company_ref = build_company_reference_schema()
    return {
        "type": "object",
        "properties": {
            "title": nullable_str,
            "company": nullable_str,
            "company_url": nullable_str,
            "role": nullable_str,
            "location": nullable_str,
            "salary": nullable_str,
            "stack": nullable_str,
            "visa": nullable_str,
            "work_types": {"type": ["array", "null"], "items": {"type": "string"}},
            "employment_types": {"type": ["array", "null"], "items": {"type": "string"}},
            "industry": nullable_str,
            "domain": nullable_str,
            "description": nullable_str,
            "companies": {
                "type": "object",
                "properties": {
                    "hiring_company": {"type": ["object", "null"], **company_ref},
                    "related_companies": {"type": "array", "items": company_ref},
                },
            },
            "scores": {
                "type": "object",
                "properties": {
                    "fit": {"type": "integer", "minimum": 0, "maximum": 100},
                    "success": {"type": "integer", "minimum": 0, "maximum": 100},
                },
                "required": ["fit", "success"],
            },
            "scores_explanation": {
                "type": "object",
                "properties": {
                    "fit_factors": {"type": "array", "items": {"type": "string"}},
                    "success_factors": {"type": "array", "items": {"type": "string"}},
                    "concerns": {"type": "array", "items": {"type": "string"}},
                },
            },
            "recommendation": {"type": "string", "enum": ["apply", "consider", "skip"]},
            "apply_reason": {"type": "string"},
            "summary": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "resume_fit": {"type": "string"},
                    "note": {"type": "string"},
                },
            },
            "skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "category": {"type": "string"},
                        "level": {"type": "integer", "minimum": 0, "maximum": 5},
                        "status": {"type": "string", "enum": ["matched", "missing", "low"]},
                        "evidence": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            "insights": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["scores", "recommendation", "apply_reason", "summary", "skills", "insights"],
    }


def build_job_analysis_prompt(
    job_text: str,
    user_profile_text: str,
    scoring_rules: str,
    resume_text: str,
    profile_documents: str = "",
    skill_breakdowns: list[dict[str, Any]] | None = None,
    target_countries: str = "your target countries",
) -> str:
    """Build the single combined analysis prompt for a job.

    profile_documents carries the latest resume and LinkedIn profile as labeled
    extra context. The resume is the authoritative source for skills and
    seniority; LinkedIn supplements it (e.g. current company, title, tenure).

    skill_breakdowns is the origin→children decomposition map (see
    ``get_breakdown_map``): composite skills that must be emitted as their
    atomic children when a posting requires them.
    """
    schema = json.dumps(build_job_analysis_output_schema(), indent=2)

    breakdown_section = ""
    if skill_breakdowns:
        lines = []
        for entry in skill_breakdowns:
            origin = (entry.get("origin") or {}).get("name")
            children = [c.get("name") for c in entry.get("children", [])]
            if origin and children:
                lines.append(f"  - '{origin}' → {', '.join(children)}")
        if lines:
            breakdown_section = (
                "\nKNOWN SKILL DECOMPOSITIONS (when a posting requires one of these composite "
                "skills, list its components as separate skills instead):\n"
                + "\n".join(lines)
                + "\n"
            )

    return f"""You are a senior career advisor for a professional evaluating a role in {target_countries}.

Analyze the job posting below and the user's profile, then produce a complete structured analysis.

JOB POSTING TEXT:
{job_text}

USER PROFILE (skills):
{user_profile_text}

USER PROFILE DOCUMENTS (latest resume and LinkedIn profile):
{profile_documents or resume_text}

SCORING RULES TO APPLY:
{scoring_rules}

Your analysis must:
1. Extract the job fields (title, company, company_url, role, location, salary, stack, visa, work_types, employment_types, industry, domain, description). Use null when a field is absent. stack lists the key tools, technologies or systems the role works with. company_url is the hiring company's website (root domain) when it can be identified from the posting; otherwise null. work_types is an array of On-site / Remote / Hybrid; employment_types is an array of Full-time / Part-time / Contract / Internship / Temporary. Usually each array has exactly one value.
1b. Identify EVERY company mentioned in the posting inside the companies block. A job may reference multiple companies (e.g. published by a recruiter while another company is hiring). Classify their relationship to the job:
   - hiring_company: the company actually hiring. Only set it with reasonable evidence ("Join Google", "Google is hiring", "At Google...", internal benefits/culture, official company domain, company career page). Do NOT assume the publishing company is the hiring company. Weak evidence (recruiter website, recruiter contact info, recruiter logo) must not promote a recruiter to hiring company. When the hiring company cannot be determined confidently, return hiring_company: null — never guess.
   - related_companies: zero or more recruiting / staffing / agency / consulting companies that published or represent the job.
   Each company entry needs name, normalized_name (strip legal suffixes: "Google LLC" → "Google"), company_type (hiring, recruiter, staffing, consulting, outsourcing, unknown), confidence (0.0-1.0: 1.0 official career page, 0.95 clearly stated employer, 0.70 likely employer, 0.40 mentioned without enough evidence), and a short reason. Do NOT merge companies — extract and classify every mention. The flat company field is a projection: hiring_company.name when present, otherwise the highest-confidence related company.
2. Score fit (0-100): how well the role matches the user's profile (skills, seniority, domain). Base this primarily on the structured CANDIDATE PROFILE when provided (it merges all sources: resume, LinkedIn, GitHub, ...); use the RESUME text as a supplement/fallback and the LinkedIn profile as supplementary evidence (current title, company, tenure, notable achievements).
3. Score success (0-100): the user's probability of getting an offer (seniority match, level, salary, competition).
4. Explain fit and success with concrete factors and list concerns (gaps, mismatches, risks).
5. Recommend apply / consider / skip based on the scores, and write a short apply_reason justifying it.
6. Summarize the job, the user's fit, and add a practical note.
7. List the skills the job requires and tag each as "matched" (user already has it), "missing" (user lacks it), or "low" (user has it but below the required level). Include the user's level (1-5), the category, and brief evidence from the posting.

   SKILL EXTRACTION RULES:
   - Emit each skill as a SINGLE ATOMIC skill, tool or competency. Split composite entries into separate skills: "NoSQL / SQL" must become two skills named "sql" and "nosql"; likewise split on ",", " and ", "&" and " or ".
   - Use lowercase names only, without versions or levels ("python 3.12" → "python", "reactjs" → "reactjs").
   - Use consistent lowercase category names that fit the candidate's profession and the posting (e.g. "tool", "domain", "method", "communication").{""
    f"{breakdown_section}"
   }8. Add 2-4 short insights (what to highlight in the application, salary/benefits notes, etc.).

OUTPUT SIZE LIMITS (critical — keep the response short so it is never truncated):
 1. description: a concise 1-2 sentence overview, at most 120 words. Do NOT copy the full posting.
 2. skills: list at most 12 skills.
 3. insights: 2-3 items only.
 4. scores_explanation: at most 3 items per list (fit_factors, success_factors, concerns).
 5. apply_reason and each summary field (summary, resume_fit, note): at most 40 words each.
 6. The JSON must be complete and valid — every string and bracket closed. Never truncate the output.
7. Return the data object itself. The schema below describes the SHAPE of your answer — do NOT reproduce it: never include "type", "properties" or "required" keys, and never nest the fields under "properties". Always fill title, company and location when they appear in the posting.

Respond ONLY with valid JSON matching exactly this schema:

{schema}
"""
