"""Company v2 list API schemas — typed DTOs for the paginated companies list."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CompanyScoresSchema(BaseModel):
    """Company intelligence score summary."""

    overall: float | None = None
    fit: float | None = None
    success: float | None = None
    overall_grade: str | None = None


class CompanyProcessingSchema(BaseModel):
    """Processing state carried on the company record."""

    status: str | None = None
    current_node: str | None = None
    progress_pct: float | None = None
    error: str | None = None


class CompanyExecutionSchema(BaseModel):
    """Latest ProcessingExecution reference for a company."""

    id: str | None = None
    status: str | None = None
    started_at: str | None = None
    finished_at: str | None = None


class CompanyMainRef(BaseModel):
    """Reference to the main company of an alias (or the company itself)."""

    id: str
    name: str


class CompanyListItemSchema(BaseModel):
    """A single company in the v2 list."""

    id: str
    name: str
    industry: str | None = None
    city: str | None = None
    country: str | None = None
    company_size: str | None = None
    company_type: str | None = None
    logo_url: str | None = None
    website: str | None = None
    description: str | None = None
    job_count: int = 0
    recruiter_job_count: int = 0
    scores: CompanyScoresSchema | None = None
    processing: CompanyProcessingSchema | None = None
    latest_processing_execution: CompanyExecutionSchema | None = None
    parent_company_id: str | None = None
    main_company: CompanyMainRef | None = None
    alias_count: int = 0
    is_alias: bool = False
    pinned: bool = False
    updated_at: str | None = None
    created_at: str | None = None


class CompanyPinRequest(BaseModel):
    """Body for PUT /api/companies/{id}/pinned."""

    pinned: bool = True


class CompanyListResponseSchema(BaseModel):
    """Cursor-paginated company list response."""

    items: list[CompanyListItemSchema] = Field(default_factory=list)
    next_cursor: str | None = None
    has_more: bool = False
    total_items: int = 0


class CompanyNoteSchema(BaseModel):
    """A single company note (stored as a note: link row)."""

    id: int
    content: str
    created_at: str | None = None


class CompanyLinkItemSchema(BaseModel):
    """A single company link."""

    id: int
    url: str | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    created_at: str | None = None


class CompanyJobRefSchema(BaseModel):
    """A slim projection of a job linked to a company."""

    id: str
    role: str | None = None
    location: str | None = None
    match: str | None = None
    score: str | None = None
    fit_score: int | None = None
    success_score: int | None = None
    overall_score: int | None = None
    rank: int | None = None


class CompanyIntelligenceSchema(BaseModel):
    """Parsed company intelligence analysis."""

    overview: Any | None = None
    culture_analysis: Any | None = None
    international_analysis: Any | None = None
    career_analysis: Any | None = None
    benefits_analysis: Any | None = None
    visa_analysis: Any | None = None
    technology_analysis: Any | None = None
    recommendation: Any | None = None
    scores: dict[str, Any] | None = None
    generated_at: str | None = None


class RecruiterJobRefSchema(BaseModel):
    """A job a recruiter publishes for a hiring company."""

    id: str
    title: str | None = None
    location: str | None = None


class RecruiterForSchema(BaseModel):
    """A hiring company that this company publishes jobs for as a recruiter."""

    company_id: str
    name: str | None = None
    job_count: int = 0
    jobs: list[RecruiterJobRefSchema] = Field(default_factory=list)


class CompanyDetailResponseSchema(BaseModel):
    """All-in-one company detail payload (mirrors the jobs v2 detail)."""

    id: str
    name: str
    website: str | None = None
    domain: str | None = None
    industry: str | None = None
    country: str | None = None
    city: str | None = None
    description: str | None = None
    company_size: str | None = None
    company_type: str | None = None
    logo_url: str | None = None
    founded_year: str | None = None
    job_count: int = 0
    status: str | None = None
    current_node: str | None = None
    progress_pct: float | None = None
    error: str | None = None
    parent_company_id: str | None = None
    main_company: CompanyMainRef | None = None
    alias_count: int = 0
    is_alias: bool = False
    pinned: bool = False
    recruiter_job_count: int = 0
    recruiter_for: list[RecruiterForSchema] = Field(default_factory=list)
    recruiter_jobs: list[CompanyJobRefSchema] = Field(default_factory=list)
    notes: list[CompanyNoteSchema] = Field(default_factory=list)
    links: list[CompanyLinkItemSchema] = Field(default_factory=list)
    intelligence: CompanyIntelligenceSchema | None = None
    scores: CompanyScoresSchema | None = None
    jobs: list[CompanyJobRefSchema] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class CompanyMainRequest(BaseModel):
    """Body for PUT /api/companies/{id}/main — null clears the relation."""

    main_company_id: str | None = None


class CompanyCreateLinkItem(BaseModel):
    """A single link on the create-company intake payload."""

    url: str = ""
    title: str | None = None
    description: str | None = None


class CompanyCreateNoteItem(BaseModel):
    """A single text note on the create-company intake payload."""

    content: str = ""


class CompanyCreateRequest(BaseModel):
    """Body for POST /api/companies — create a company from intake."""

    name: str = ""
    notes: list[CompanyCreateNoteItem] | list[dict[str, Any]] = Field(default_factory=list)
    links: list[CompanyCreateLinkItem] | list[str] = Field(default_factory=list)
    source: str = "web"
    input_type: str = "url"
    queue: bool = True


class CompanyCreateResponse(BaseModel):
    """Response for POST /api/companies."""

    id: str
    name: str
    source: str | None = None
    input_type: str | None = None
    status: str
    execution_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CompanyUpdateRequest(BaseModel):
    """Body for PUT /api/companies/{id} — partial update of profile fields."""

    name: str | None = None
    industry: str | None = None
    city: str | None = None
    country: str | None = None
    logo_url: str | None = None
    website: str | None = None
    domain: str | None = None
    description: str | None = None
    company_size: str | None = None
    company_type: str | None = None


class CompanyNoteRequest(BaseModel):
    """Body for POST /api/companies/{id}/notes and PUT .../notes/{note_id}."""

    content: str = ""


class CompanyLinkRequest(BaseModel):
    """Body for POST /api/companies/{id}/links and PUT .../links/{link_id}."""

    url: str = ""
    title: str | None = None
    description: str | None = None
