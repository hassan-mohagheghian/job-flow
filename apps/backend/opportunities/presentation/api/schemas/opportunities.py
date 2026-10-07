"""Pydantic schemas for the Opportunities API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from opportunities.domain.entities.opportunity import (
    EvaluationStatus,
    OpportunitySource,
    OpportunityStatus,
)


class CreateOpportunityRequest(BaseModel):
    source: str = OpportunitySource.MANUAL
    source_message_id: str | None = None
    sender: str | None = None
    sender_email: str | None = None
    received_at: str | None = None
    subject: str | None = None
    raw_content: str

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


class UpdateOpportunityLinksRequest(BaseModel):
    job_id: str | None = None
    company_id: str | None = None


class UpdateOpportunityStatusRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if str(v) not in OpportunityStatus.ALL:
            raise ValueError(f"status must be one of {', '.join(OpportunityStatus.ALL)}")
        return str(v)


class OpportunityListItemSchema(BaseModel):
    id: str
    title: str = "Unknown role"
    company_name: str | None = None
    job_title: str | None = None
    source: str = OpportunitySource.MANUAL
    status: str = OpportunityStatus.NEW
    evaluation_status: str = EvaluationStatus.PENDING
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
    extracted_urls: list[str] = Field(default_factory=list)
    extracted: dict[str, Any] = Field(default_factory=dict)
    company_id: str | None = None
    company_name: str | None = None
    job_id: str | None = None
    job_title: str | None = None
    status: str = OpportunityStatus.NEW
    evaluation_status: str = EvaluationStatus.PENDING
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
    evaluations: list[OpportunityEvaluationSchema] = Field(default_factory=list)


def build_list_item(row: dict[str, Any]) -> OpportunityListItemSchema:
    return OpportunityListItemSchema(
        id=row["id"],
        title=row.get("title") or "Unknown role",
        company_name=row.get("company_name"),
        job_title=row.get("job_title"),
        source=row.get("source") or OpportunitySource.MANUAL,
        status=row.get("status") or OpportunityStatus.NEW,
        evaluation_status=row.get("evaluation_status") or EvaluationStatus.PENDING,
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
        extracted_urls=list(row.get("extracted_urls") or []),
        extracted=dict(row.get("extracted") or {}),
        company_id=row.get("company_id"),
        company_name=row.get("company_name"),
        job_id=row.get("job_id"),
        job_title=row.get("job_title"),
        status=row.get("status") or OpportunityStatus.NEW,
        evaluation_status=row.get("evaluation_status") or EvaluationStatus.PENDING,
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
        evaluations=[OpportunityEvaluationSchema(**e) for e in (evaluations or [])],
    )


__all__ = [
    "CreateOpportunityRequest",
    "UpdateOpportunityLinksRequest",
    "UpdateOpportunityStatusRequest",
    "OpportunityListItemSchema",
    "OpportunityListResponse",
    "OpportunityEvaluationSchema",
    "OpportunityDetailResponse",
    "build_list_item",
    "build_detail_response",
]
