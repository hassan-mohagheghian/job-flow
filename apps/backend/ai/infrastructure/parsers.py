"""Structured Output Parsers — Pydantic models for AI responses.

Every AI response should produce structured outputs.
Prefer Pydantic models and validation over free-form parsing.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

# Keys that only belong to a JSON Schema document, never to the answer data.
_SCHEMA_METADATA_KEYS = frozenset(
    {"type", "properties", "required", "$schema", "additionalProperties"}
)
_SCHEMA_NODE_KEYS = frozenset(
    {
        "type",
        "items",
        "properties",
        "required",
        "enum",
        "minimum",
        "maximum",
        "default",
        "description",
        "title",
        "additionalProperties",
    }
)


def _is_schema_node(value: Any) -> bool:
    """True when a value is a JSON Schema field definition (not answer data)."""
    return (
        isinstance(value, dict)
        and "type" in value
        and set(value).issubset(_SCHEMA_NODE_KEYS)
    )


def unwrap_schema_echo(payload: dict[str, Any]) -> dict[str, Any]:
    """Unwrap a response that echoed the output schema instead of the data.

    Prompt-based providers (opencode) sometimes answer with the schema skeleton
    filled in::

        {"type": "object", "properties": {"title": "...", ...},
         "scores": {...}, "recommendation": "..."}

    Pydantic would ignore the unknown wrapper keys, so all top-level fields
    (`title`, `company`, `location`, ...) silently default to ``None``. This
    function merges the real values from ``properties`` with the sibling keys
    and drops the schema metadata.

    A pure schema echo (every property is a ``{"type": ...}`` definition) is
    returned unchanged so downstream validation rejects it.
    """
    if payload.get("type") != "object":
        return payload

    properties = payload.get("properties")
    if not isinstance(properties, dict):
        return payload

    data = {name: value for name, value in properties.items() if not _is_schema_node(value)}
    if not data:
        return payload

    siblings = {
        key: value
        for key, value in payload.items()
        if key not in _SCHEMA_METADATA_KEYS
    }
    # ``properties`` holds the extracted fields, so it wins on collisions.
    return {**siblings, **data}


class JobExtractionOutput(BaseModel):
    """Structured output for job extraction."""
    title: str = Field(description="Job title/position")
    company: str = Field(description="Company name")
    location: str = Field(default="", description="Job location")
    salary: str = Field(default="", description="Salary range")
    stack: str = Field(default="", description="Required tech stack")
    description: str = Field(default="", description="Job description")
    requirements: str = Field(default="", description="Job requirements")
    benefits: str = Field(default="", description="Benefits offered")
    url: str = Field(default="", description="Job posting URL")

    @field_validator("title", "company")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if v else ""


class JobScoreOutput(BaseModel):
    """Structured output for job scoring."""
    fit_score: int = Field(ge=0, le=100, description="Fit score (0-100)")
    success_score: int = Field(ge=0, le=100, description="Success score (0-100)")
    overall_score: int = Field(ge=0, le=100, description="Overall score (0-100)")
    match_level: str = Field(description="Match level: High/Medium/Low")
    key_factors: list[str] = Field(default_factory=list, description="Key match factors")
    concerns: list[str] = Field(default_factory=list, description="Potential concerns")

    @field_validator("match_level")
    @classmethod
    def validate_match_level(cls, v: str) -> str:
        valid_levels = {"High", "Medium", "Low"}
        if v not in valid_levels:
            raise ValueError(f"match_level must be one of {valid_levels}")
        return v


class JobSummaryOutput(BaseModel):
    """Structured output for job summary."""
    key_responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    attractive_factors: list[str] = Field(default_factory=list)
    career_growth: str = Field(default="")
    culture_highlights: str = Field(default="")
    summary_text: str = Field(default="")


class SkillExtractionOutput(BaseModel):
    """Structured output for skill extraction."""
    skills: list[str] = Field(default_factory=list, description="Extracted skills")
    categories: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Skills grouped by category"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Extraction confidence")
