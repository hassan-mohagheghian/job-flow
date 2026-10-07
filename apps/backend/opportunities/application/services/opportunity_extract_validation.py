"""Strict schema validation for the opportunity.extract LLM output.

Only output that validates against this model is accepted and persisted.
Anything else is rejected by OpportunityService and surfaced as a clean
error. Mirrors the JSON schema built by build_opportunity_extract_output_schema().
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from opportunities.domain.entities.opportunity import FieldState


def _coerce_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


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


def _coerce_state(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in FieldState.ALL else FieldState.UNKNOWN


def _clamp_confidence(value: Any) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, n))


class ExtractedCompany(BaseModel):
    name: str | None = None
    website: str | None = None
    confidence: float = 0.0
    state: str = FieldState.UNKNOWN

    @field_validator("name", "website", mode="before")
    @classmethod
    def coerce_optional(cls, v: Any) -> str | None:
        return _coerce_optional_str(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, v: Any) -> float:
        return _clamp_confidence(v)

    @field_validator("state", mode="before")
    @classmethod
    def coerce_state(cls, v: Any) -> str:
        return _coerce_state(v)


class ExtractedRecruiter(BaseModel):
    name: str | None = None
    email: str | None = None
    state: str = FieldState.UNKNOWN

    @field_validator("name", "email", mode="before")
    @classmethod
    def coerce_optional(cls, v: Any) -> str | None:
        return _coerce_optional_str(v)

    @field_validator("state", mode="before")
    @classmethod
    def coerce_state(cls, v: Any) -> str:
        return _coerce_state(v)


class ExtractedLocation(BaseModel):
    value: str | None = None
    state: str = FieldState.UNKNOWN

    @field_validator("value", mode="before")
    @classmethod
    def coerce_optional(cls, v: Any) -> str | None:
        return _coerce_optional_str(v)

    @field_validator("state", mode="before")
    @classmethod
    def coerce_state(cls, v: Any) -> str:
        return _coerce_state(v)


class ExtractedSkill(BaseModel):
    name: str = ""
    level: int | None = None
    state: str = FieldState.UNKNOWN

    @field_validator("name", mode="before")
    @classmethod
    def coerce_name(cls, v: Any) -> str:
        return _coerce_str(v).lower()

    @field_validator("state", mode="before")
    @classmethod
    def coerce_state(cls, v: Any) -> str:
        return _coerce_state(v)


class ExtractedSponsorship(BaseModel):
    mentions: list[str] = Field(default_factory=list)
    requires_sponsorship: bool | None = None
    state: str = FieldState.UNKNOWN

    @field_validator("mentions", mode="before")
    @classmethod
    def coerce_list(cls, v: Any) -> list[str]:
        return _coerce_str_list(v)

    @field_validator("state", mode="before")
    @classmethod
    def coerce_state(cls, v: Any) -> str:
        return _coerce_state(v)


class OpportunityExtractOutput(BaseModel):
    role_title: str | None = None
    role_state: str = FieldState.UNKNOWN
    company: ExtractedCompany = Field(default_factory=ExtractedCompany)
    job_urls: list[str] = Field(default_factory=list)
    job_description_present: bool = False
    recruiter: ExtractedRecruiter = Field(default_factory=ExtractedRecruiter)
    location: ExtractedLocation = Field(default_factory=ExtractedLocation)
    work_modes: list[str] = Field(default_factory=list)
    employment_types: list[str] = Field(default_factory=list)
    salary: str | None = None
    skills: list[ExtractedSkill] = Field(default_factory=list)
    experience: str | None = None
    sponsorship: ExtractedSponsorship = Field(default_factory=ExtractedSponsorship)
    contacts: list[str] = Field(default_factory=list)
    application_instructions: str | None = None
    uncertainties: list[str] = Field(default_factory=list)

    @field_validator("role_title", "salary", "experience", "application_instructions", mode="before")
    @classmethod
    def coerce_optional(cls, v: Any) -> str | None:
        return _coerce_optional_str(v)

    @field_validator("role_state", mode="before")
    @classmethod
    def coerce_state(cls, v: Any) -> str:
        return _coerce_state(v)

    @field_validator("job_urls", "work_modes", "employment_types", "contacts", "uncertainties", mode="before")
    @classmethod
    def coerce_lists(cls, v: Any) -> list[str]:
        return _coerce_str_list(v)


__all__ = [
    "OpportunityExtractOutput",
    "ExtractedCompany",
    "ExtractedRecruiter",
    "ExtractedLocation",
    "ExtractedSkill",
    "ExtractedSponsorship",
]
