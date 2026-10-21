"""Pydantic schemas for the Applications API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from applications.domain.entities.application import ApplicationStatus, DocumentType


class CreateApplicationRequest(BaseModel):
    job_id: str
    seen_at: str | None = None

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("job_id must not be empty")
        return str(v).strip()


class UpdateApplicationRequest(BaseModel):
    status: str | None = None
    applied_at: str | None = None
    timeline_at: str | None = None


class CreateFollowUpRequest(BaseModel):
    scheduled_at: str | None = None
    note: str = ""


class UpdateFollowUpRequest(BaseModel):
    scheduled_at: str | None = None
    note: str | None = None
    completed: bool | None = None


class CreateNoteRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("content must not be empty")
        return v.strip()


class UpdateStatusEventRequest(BaseModel):
    changed_at: str | None = None


class UpdateDocumentRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("content must not be empty")
        return v


class ApplicationStatusEventSchema(BaseModel):
    id: str
    application_id: str
    status: str = ApplicationStatus.SEEN
    changed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ApplicationFollowUpSchema(BaseModel):
    id: str
    application_id: str
    scheduled_at: str | None = None
    note: str = ""
    completed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    @property
    def completed(self) -> bool:
        return self.completed_at is not None


class ApplicationNoteSchema(BaseModel):
    id: str
    application_id: str
    content: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class ApplicationDocumentSchema(BaseModel):
    id: str
    application_id: str
    document_type: str
    version: int
    content: str = ""
    created_at: str | None = None
    updated_at: str | None = None


class ApplicationDetailResponse(BaseModel):
    id: str
    job_id: str
    status: str = ApplicationStatus.SEEN
    applied_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    status_timeline: list[ApplicationStatusEventSchema] = Field(default_factory=list)
    follow_ups: list[ApplicationFollowUpSchema] = Field(default_factory=list)
    notes: list[ApplicationNoteSchema] = Field(default_factory=list)
    documents: list[ApplicationDocumentSchema] = Field(default_factory=list)


class ApplicationStatusCountSchema(BaseModel):
    status: str
    count: int = 0


class ApplicationStatusDistributionResponse(BaseModel):
    items: list[ApplicationStatusCountSchema] = Field(default_factory=list)
    total: int = 0


class GenerateResponse(BaseModel):
    execution_id: str
    status: str
    artifact: str = ""


class DeleteResponse(BaseModel):
    status: str = "deleted"


def build_detail_response(
    application: dict[str, Any],
    follow_ups: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    status_timeline: list[dict[str, Any]] | None = None,
    notes: list[dict[str, Any]] | None = None,
) -> ApplicationDetailResponse:
    return ApplicationDetailResponse(
        id=application["id"],
        job_id=application.get("job_id", ""),
        status=application.get("status", ApplicationStatus.SEEN),
        applied_at=application.get("applied_at"),
        created_at=application.get("created_at"),
        updated_at=application.get("updated_at"),
        status_timeline=[ApplicationStatusEventSchema(**e) for e in (status_timeline or [])],
        follow_ups=[ApplicationFollowUpSchema(**f) for f in follow_ups],
        notes=[ApplicationNoteSchema(**n) for n in (notes or [])],
        documents=[ApplicationDocumentSchema(**d) for d in documents],
    )


__all__ = [
    "CreateApplicationRequest",
    "UpdateApplicationRequest",
    "CreateFollowUpRequest",
    "UpdateFollowUpRequest",
    "CreateNoteRequest",
    "UpdateStatusEventRequest",
    "UpdateDocumentRequest",
    "ApplicationStatusEventSchema",
    "ApplicationFollowUpSchema",
    "ApplicationNoteSchema",
    "ApplicationDocumentSchema",
    "ApplicationDetailResponse",
    "ApplicationStatusCountSchema",
    "ApplicationStatusDistributionResponse",
    "GenerateResponse",
    "DeleteResponse",
    "build_detail_response",
]
