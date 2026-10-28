"""Pydantic schemas for the Opportunities API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from opportunities.domain.entities.opportunity import (
    EvaluationStatus,
    OpportunitySource,
    OpportunityStatus,
)


class CreateLinkRequest(BaseModel):
    """A user-added titled link on an opportunity (e.g. the LinkedIn post)."""

    title: str | None = None
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        value = str(v or "").strip()
        if not value:
            raise ValueError("url must not be empty")
        if not value.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return value


class CreateNoteRequest(BaseModel):
    title: str | None = None
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not str(v or "").strip():
            raise ValueError("content must not be empty")
        return str(v)


class CreateOpportunityRequest(BaseModel):
    source: str = OpportunitySource.MANUAL
    source_message_id: str | None = None
    sender: str | None = None
    sender_email: str | None = None
    received_at: str | None = None
    subject: str | None = None
    raw_content: str
    base_url: str | None = None
    notes: list[CreateNoteRequest] | None = None
    links: list[CreateLinkRequest] | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        source = str(v or "").strip().lower()
        if source not in OpportunitySource.ALL:
            raise ValueError(f"source must be one of {', '.join(OpportunitySource.ALL)}")
        return source

    @field_validator("raw_content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not str(v or "").strip():
            raise ValueError("raw_content must not be empty")
        return str(v)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str | None) -> str | None:
        value = str(v or "").strip()
        if not value:
            return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return value


class UpdateOpportunityLinksRequest(BaseModel):
    job_id: str | None = None
    company_id: str | None = None


class UpdateOpportunityBaseUrlRequest(BaseModel):
    """Set or clear the opportunity's sourcing base URL (empty clears)."""

    base_url: str | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str | None) -> str | None:
        value = str(v or "").strip()
        if not value:
            return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return value


class UpdateOpportunityStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if str(v) not in OpportunityStatus.ALL:
            raise ValueError(f"status must be one of {', '.join(OpportunityStatus.ALL)}")
        return str(v)


class DismissOpportunityRequest(BaseModel):
    """Schema for dismissing or undismissing an opportunity."""

    dismissed: bool
    note: str | None = None


class OpportunityListItemSchema(BaseModel):
    id: str
    title: str = "Unknown role"
    company_name: str | None = None
    job_title: str | None = None
    source: str = OpportunitySource.MANUAL
    status: str = OpportunityStatus.NEW
    evaluation_status: str = EvaluationStatus.PENDING
    dismissed: bool = False
    overall_score: int | None = None
    fit_score: int | None = None
    success_score: int | None = None
    recommendation: str | None = None
    next_action: str | None = None
    job_id: str | None = None
    company_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class OpportunityListResponse(BaseModel):
    items: list[OpportunityListItemSchema] = Field(default_factory=list)
    total: int = 0


class OpportunityEvaluationSchema(BaseModel):
    id: str
    opportunity_id: str
    status: str
    evaluation_status: str = EvaluationStatus.COMPLETE
    fit_score: int | None = None
    success_score: int | None = None
    overall_score: int | None = None
    recommendation: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class OpportunityNoteSchema(BaseModel):
    id: str
    opportunity_id: str
    title: str | None = None
    content: str = ""
    author: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class OpportunityLinkSchema(BaseModel):
    id: str
    opportunity_id: str
    title: str | None = None
    url: str
    created_at: str | None = None
    updated_at: str | None = None


class OpportunityDetailResponse(BaseModel):
    id: str
    title: str = "Unknown role"
    source: str = OpportunitySource.MANUAL
    source_message_id: str | None = None
    sender: str | None = None
    sender_email: str | None = None
    received_at: str | None = None
    subject: str | None = None
    raw_content: str = ""
    base_url: str | None = None
    extracted_urls: list[str] = Field(default_factory=list)
    extracted: dict[str, Any] = Field(default_factory=dict)
    company_id: str | None = None
    company_name: str | None = None
    job_id: str | None = None
    job_title: str | None = None
    status: str = OpportunityStatus.NEW
    evaluation_status: str = EvaluationStatus.PENDING
    dismissed: bool = False
    fit_score: int | None = None
    success_score: int | None = None
    overall_score: int | None = None
    recommendation: str | None = None
    evaluation: dict[str, Any] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list)
    application_path: dict[str, Any] = Field(default_factory=dict)
    next_action: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    duplicate: bool = False
    created_job: bool = False
    evaluations: list[OpportunityEvaluationSchema] = Field(default_factory=list)
    notes: list[OpportunityNoteSchema] = Field(default_factory=list)
    links: list[OpportunityLinkSchema] = Field(default_factory=list)


def build_list_item(row: dict[str, Any]) -> OpportunityListItemSchema:
    return OpportunityListItemSchema(
        id=row["id"],
        title=row.get("title") or "Unknown role",
        company_name=row.get("company_name"),
        job_title=row.get("job_title"),
        source=row.get("source") or OpportunitySource.MANUAL,
        status=row.get("status") or OpportunityStatus.NEW,
        evaluation_status=row.get("evaluation_status") or EvaluationStatus.PENDING,
        dismissed=bool(row.get("dismissed")),
        overall_score=row.get("overall_score"),
        fit_score=row.get("fit_score"),
        success_score=row.get("success_score"),
        recommendation=row.get("recommendation"),
        next_action=row.get("next_action"),
        job_id=row.get("job_id"),
        company_id=row.get("company_id"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def build_detail_response(
    row: dict[str, Any],
    evaluations: list[dict[str, Any]] | None = None,
    duplicate: bool = False,
    notes: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
) -> OpportunityDetailResponse:
    return OpportunityDetailResponse(
        id=row["id"],
        title=row.get("title") or "Unknown role",
        source=row.get("source") or OpportunitySource.MANUAL,
        source_message_id=row.get("source_message_id"),
        sender=row.get("sender"),
        sender_email=row.get("sender_email"),
        received_at=row.get("received_at"),
        subject=row.get("subject"),
        raw_content=row.get("raw_content") or "",
        base_url=row.get("base_url"),
        extracted_urls=list(row.get("extracted_urls") or []),
        extracted=dict(row.get("extracted") or {}),
        company_id=row.get("company_id"),
        company_name=row.get("company_name"),
        job_id=row.get("job_id"),
        job_title=row.get("job_title"),
        status=row.get("status") or OpportunityStatus.NEW,
        evaluation_status=row.get("evaluation_status") or EvaluationStatus.PENDING,
        dismissed=bool(row.get("dismissed")),
        fit_score=row.get("fit_score"),
        success_score=row.get("success_score"),
        overall_score=row.get("overall_score"),
        recommendation=row.get("recommendation"),
        evaluation=dict(row.get("evaluation") or {}),
        missing_information=list(row.get("missing_information") or []),
        application_path=dict(row.get("application_path") or {}),
        next_action=row.get("next_action"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
        duplicate=duplicate,
        created_job=bool(row.get("created_job", False)),
        evaluations=[OpportunityEvaluationSchema(**e) for e in (evaluations or [])],
        notes=[OpportunityNoteSchema(**n) for n in (notes or [])],
        links=[OpportunityLinkSchema(**l) for l in (links or [])],
    )


__all__ = [
    "CreateOpportunityRequest",
    "CreateNoteRequest",
    "CreateLinkRequest",
    "UpdateOpportunityLinksRequest",
    "UpdateOpportunityBaseUrlRequest",
    "UpdateOpportunityStatusRequest",
    "DismissOpportunityRequest",
    "OpportunityListItemSchema",
    "OpportunityListResponse",
    "OpportunityEvaluationSchema",
    "OpportunityNoteSchema",
    "OpportunityLinkSchema",
    "OpportunityDetailResponse",
    "build_list_item",
    "build_detail_response",
]
