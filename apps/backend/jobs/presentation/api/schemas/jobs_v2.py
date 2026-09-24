"""New Jobs List API schemas — JobListItem DTO matching docs/domain/jobs/job-list-item.md."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class JobNoteItem(BaseModel):
    """A free-form note attached to a job."""

    title: str | None = None
    content: str


class JobLinkItem(BaseModel):
    """A related URL attached to a job."""

    title: str | None = None
    url: str


class ScoresSchema(BaseModel):
    overall: int | None = None
    fit: int | None = None
    success: int | None = None


class UpdateJobRequest(BaseModel):
    """Schema for partially updating a Job's core data.

    All fields are optional; omitted fields are left unchanged. A field set to
    None leaves the stored value unchanged; an empty string clears it.
    """

    title: str | None = None
    role: str | None = None
    company: str | None = None
    location: str | None = None
    url: str | None = None
    work_types: list[str] | None = None
    employment_types: list[str] | None = None
    visa: str | None = None
    salary: str | None = None
    description: str | None = None
    notes: list[JobNoteItem] | None = None
    links: list[JobLinkItem] | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not str(v).startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v

    @field_validator("links")
    @classmethod
    def validate_links(cls, v: list[JobLinkItem] | None) -> list[JobLinkItem] | None:
        if v is None:
            return v
        for item in v:
            if not str(item.url).startswith(("http://", "https://")):
                raise ValueError("each link url must start with http:// or https://")
        return v

    @field_validator("work_types", "employment_types", mode="before")
    @classmethod
    def coerce_string_list(cls, v: Any) -> list[str] | None:
        if v is None:
            return v
        if isinstance(v, str):
            items = [x.strip() for x in v.split(",") if x.strip()]
        elif isinstance(v, list):
            items = [str(x).strip() for x in v if str(x).strip()]
        else:
            raise ValueError("must be a list of strings")
        return items or None


class ProcessingExecutionSchema(BaseModel):
    id: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None


class JobListItemSchema(BaseModel):
    id: str
    title: str | None = None
    company_name: str | None = Field(default=None, validation_alias="company")
    location: str | None = None
    remote: bool | None = None
    visa_sponsorship: bool | None = None
    job_status: str | None = Field(default=None, validation_alias="status")
    latest_processing_execution: ProcessingExecutionSchema | None = None
    scores: ScoresSchema | None = None
    recommendation: str | None = None
    pinned: bool = False
    dismissed: bool = False
    tags: list[str] = Field(default_factory=list)
    rank: int | None = None
    tracking_status: str | None = None
    easy_apply: bool | None = None
    updated_at: str | None = None
    created_at: str | None = None

    model_config = {"populate_by_name": True, "from_attributes": True}


class PinJobRequest(BaseModel):
    """Schema for pinning or unpinning a job."""

    pinned: bool


class DismissJobRequest(BaseModel):
    """Schema for dismissing or undismissing a job."""

    dismissed: bool
    note: str | None = None


class SetJobCompanyRequest(BaseModel):
    """Schema for linking a job to a company.

    ``company_id`` set to ``None`` (or an empty string) unlinks the job from
    its company without touching the stored company name.
    """

    company_id: str | None = None

    @field_validator("company_id")
    @classmethod
    def normalize_company_id(cls, v: str | None) -> str | None:
        if v is None or not str(v).strip():
            return None
        return str(v).strip()


class SetJobTagsRequest(BaseModel):
    """Schema for setting tags on a job."""

    tags: list[str] = Field(default_factory=list)


class PaginationSchema(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class CursorPaginationSchema(BaseModel):
    total_items: int
    next_cursor: str | None = None
    has_more: bool = False


class JobListResponseSchema(BaseModel):
    items: list[JobListItemSchema] = Field(default_factory=list)
    pagination: PaginationSchema | None = None
    cursor_pagination: CursorPaginationSchema | None = None


class JobTimelineDaySchema(BaseModel):
    date: str
    count: int


class JobTimelineResponseSchema(BaseModel):
    days: list[JobTimelineDaySchema] = Field(default_factory=list)
    total: int = 0


class JobDetailWorkflowStepSchema(BaseModel):
    id: str
    title: str
    status: str = "pending"
    progress: float | None = None
    displayable: bool = True
    children: list["JobDetailWorkflowStepSchema"] = Field(default_factory=list)
    error: dict[str, str] | None = None
    started_at: str | None = None
    completed_at: str | None = None


class JobDetailWorkflowSchema(BaseModel):
    id: str
    name: str = "Job Context Preparation"
    status: str = "pending"
    current_step: JobDetailWorkflowStepSchema | None = None
    progress: float | None = None
    steps: list[JobDetailWorkflowStepSchema] = Field(default_factory=list)


class JobDetailExecutionSchema(BaseModel):
    execution_id: str
    status: str
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    error: dict[str, str] | None = None
    current_step: str | None = None
    workflow: JobDetailWorkflowSchema | None = None


class JobAnalysisScoresExplanationSchema(BaseModel):
    fit_factors: list[str] = Field(default_factory=list)
    success_factors: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)


class JobAnalysisSummarySchema(BaseModel):
    summary: str = ""
    resume_fit: str = ""
    note: str = ""


class JobAnalysisSkillSchema(BaseModel):
    name: str
    category: str | None = None
    level: int | None = None
    status: str | None = None
    evidence: str | None = None


class JobAnalysisBlockSchema(BaseModel):
    recommendation: str | None = None
    apply_reason: str | None = None
    scores_explanation: JobAnalysisScoresExplanationSchema | None = None
    summary: JobAnalysisSummarySchema | None = None
    skills: list[JobAnalysisSkillSchema] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    generated_at: str | None = None


class RelatedCompanySchema(BaseModel):
    """A company associated with this job (hiring or recruiter)."""

    company_id: str
    name: str | None = None
    role: str | None = None
    company_type: str | None = None
    confidence: float | None = None
    reason: str | None = None


class JobDetailResponseSchema(BaseModel):
    id: str
    title: str | None = None
    company_name: str | None = Field(default=None, validation_alias="company")
    company_id: str | None = None
    company_type: str | None = None
    role: str | None = None
    location: str | None = None
    work_types: list[str] | None = None
    employment_types: list[str] | None = None
    salary: str | None = None
    visa: str | None = None
    url: str | None = None
    status: str | None = None
    rank: int | None = None
    scores: ScoresSchema | None = None
    latest_processing_execution: JobDetailExecutionSchema | None = None
    analysis: JobAnalysisBlockSchema | None = None
    related_companies: list[RelatedCompanySchema] = Field(default_factory=list)
    description: str | None = None
    notes: list[JobNoteItem] = Field(default_factory=list)
    links: list[JobLinkItem] = Field(default_factory=list)
    tracking_status: str | None = None
    dismissed: bool = False
    pinned: bool = False
    easy_apply: bool | None = None
    updated_at: str | None = None
    created_at: str | None = None

    model_config = {"populate_by_name": True, "from_attributes": True}
