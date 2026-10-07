"""Strict schema validation for the opportunity.evaluate LLM output.

Only output that validates against this model is accepted. Anything else is
rejected by OpportunityService and surfaced as a clean error. Mirrors the JSON
schema built by build_opportunity_evaluate_output_schema().
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

_MATCH_VALUES = ("match", "partial", "mismatch", "unknown")


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return []


def _clamp_score(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return None
    return max(0, min(100, n))


def _coerce_match(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in _MATCH_VALUES else "unknown"


class OpportunityEvaluateOutput(BaseModel):
    fit: int | None = None
    success: int | None = None
    technical_match: int | None = None
    experience_match: int | None = None
    location_match: str = "unknown"
    seniority_match: str = "unknown"
    employment_match: str = "unknown"
    salary_match: str = "unknown"
    authorization: str | None = None
    career_alignment: int | None = None
    concerns: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    unknown_information: list[str] = Field(default_factory=list)
    enough_to_apply: bool = False
    recommended_next_action: str | None = None

    @field_validator("fit", "success", "technical_match", "experience_match", "career_alignment", mode="before")
    @classmethod
    def coerce_scores(cls, v: Any) -> int | None:
        return _clamp_score(v)

    @field_validator("location_match", "seniority_match", "employment_match", "salary_match", mode="before")
    @classmethod
    def coerce_matches(cls, v: Any) -> str:
        return _coerce_match(v)

    @field_validator("authorization", "recommended_next_action", mode="before")
    @classmethod
    def coerce_optional(cls, v: Any) -> str | None:
        return _coerce_optional_str(v)

    @field_validator("concerns", "missing_requirements", "unknown_information", mode="before")
    @classmethod
    def coerce_lists(cls, v: Any) -> list[str]:
        return _coerce_str_list(v)


__all__ = ["OpportunityEvaluateOutput"]
