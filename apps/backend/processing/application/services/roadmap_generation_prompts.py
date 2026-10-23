"""Roadmap Generation prompt builders — the single LLM call that produces a
job-preparation roadmap from existing Career Intelligence.

Each builder produces a versioned prompt plus its strict output JSON schema.
The LLM call always goes through LLMService (AGENTS.md rule #1) and the result
is validated against the mirrored Pydantic models in
``roadmap_generation_validation``.

The generator is a *consumer* of existing intelligence: the prompt is grounded
in the persisted job analysis, company intelligence and candidate profile. It
never re-analyzes the job, company or user (spec 144 §13).
"""

from __future__ import annotations

import json
from typing import Any

ROADMAP_GENERATION_PROMPT_VERSION = "1.0.2"
ROADMAP_GENERATION_SCHEMA_VERSION = "1.0.0"


def build_roadmap_output_schema() -> dict[str, Any]:
    """JSON schema for the AI-generated job-preparation roadmap.

    The LLM must return a roadmap title, a JOB goal and an ordered list of
    outcome-based milestones (required). Each milestone carries its own skills
    and concrete tasks. Milestone/task counts are capped (≤8 × ≤8) per spec
    §14 so the call stays small and actionable.
    """
    task_item = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "estimated_effort": {"type": "string"},
            "success_criteria": {"type": "string"},
        },
        "required": ["title"],
    }
    milestone_item = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string"},
            "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
            "success_criteria": {"type": "string"},
            "skills": {"type": "array", "items": {"type": "string"}},
            "tasks": {"type": "array", "items": task_item},
        },
        "required": ["title"],
    }
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "goal": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["JOB"]},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
            "milestones": {"type": "array", "items": milestone_item},
        },
        "required": ["milestones"],
    }


def build_roadmap_prompt(context: dict[str, str]) -> str:
    """Build the roadmap generation prompt (grounded in job + skills + company + candidate)."""
    schema = json.dumps(build_roadmap_output_schema(), indent=2)
    return f"""You are a senior career coach guiding a professional toward the role they are targeting.

Build a practical, prioritized job-preparation ROADMAP from the structured intelligence below. Never re-analyze the job, company or candidate — use the persisted analysis, tagged skills and scores as the source of truth.

{_sections(context, ["job", "job_skills", "company", "candidate"])}

ROADMAP RULES:
1. milestones: between 3 and 8. Each milestone is a meaningful OUTCOME the user achieves (e.g. "Ship a Kafka-based project", "Pass the interview loop"), never a bare topic.
   - title: short outcome statement.
   - description: 1-2 sentences on why this milestone matters for THIS role.
   - priority: "critical" (blocks the application / core to the role), "high", "medium", or "low".
   - success_criteria: how the user will know the milestone is done (concrete, verifiable).
   - skills: only the skills this milestone develops, picked from the job-required skills tagged by the analysis (use each skill's canonical name). At most 5 per milestone.
   - tasks: between 1 and 8 concrete, actionable steps. Each task has a title, a short description, an estimated_effort ("3-4 hours", "2 days", ...), and a success_criteria.
2. Order milestones to close the smallest meaningful set of gaps first (prioritize skills tagged "missing" then "low" in the analysis). Focus on the role's core requirements — do not pad the roadmap.
3. goal: the goal type is always "JOB"; give it a concise title and description.
4. title: a short, human-readable roadmap title.

Respond ONLY with valid JSON matching exactly this schema:

{schema}
"""


def _sections(context: dict[str, str], keys: list[str]) -> str:
    return "\n\n".join(context.get(k) or f"{k.upper()}:\n  (no data available)" for k in keys)