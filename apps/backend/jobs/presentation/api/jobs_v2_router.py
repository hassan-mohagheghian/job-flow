"""New Jobs List API router — registered before legacy routes to avoid path conflicts."""

from __future__ import annotations

import json
import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi import status as http_status

from shared.application.exceptions import JobAlreadyExistsError

from jobs.domain.services.job_url_rules import find_duplicate_job
from jobs.presentation.api.schemas.jobs import CreateJobRequest, CreateJobResponse
from jobs.presentation.api.schemas.jobs_v2 import (
    JobListItemSchema,
    JobListResponseSchema,
    PaginationSchema,
    CursorPaginationSchema,
    ScoresSchema,
    ProcessingExecutionSchema,
    JobDetailResponseSchema,
    JobDetailExecutionSchema,
    JobDetailWorkflowSchema,
    JobDetailWorkflowStepSchema,
    JobAnalysisBlockSchema,
    JobAnalysisScoresExplanationSchema,
    JobAnalysisSummarySchema,
    JobAnalysisSkillSchema,
    UpdateJobRequest,
    JobNoteItem,
    JobLinkItem,
    PinJobRequest,
    DismissJobRequest,
    SetJobCompanyRequest,
    SetJobTagsRequest,
    JobTimelineResponseSchema,
)
from jobs.application.use_cases.list_jobs_v2 import ListJobsV2UseCase, ListJobsV2Request
from jobs.infrastructure import SQLAlchemyJobRepository
from jobs.infrastructure.repositories.sa_job_analysis_repository import SQLAlchemyJobAnalysisRepository
from jobs.infrastructure.repositories.sa_job_company_repository import SQLAlchemyJobCompanyRepository
from jobs.infrastructure.repositories.sa_summary_repository import SQLAlchemySummaryRepository
from processing.infrastructure import SQLAlchemyProcessingExecutionRepository
from processing.domain.enums import ExecutionStatus
from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
from applications.infrastructure import SQLAlchemyApplicationRepository
from dependencies import (
    get_job_repo,
    get_processing_execution_repo,
    get_job_analysis_repo,
    get_job_company_repo,
    get_summary_repo,
    get_company_repo,
    get_application_repo,
)
router = APIRouter()

# Job-tracking statuses surfaced on the jobs list. Derived from the
# application funnel; "not_applied" means the job has no application yet.
TRACKING_STATUSES = {
    "not_applied",
    "seen",
    "preparing",
    "ready_to_apply",
    "applied",
    "interview",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
    "expired",
}



def _queue_job_for_processing(job_id: str, exec_repo, user_id: str = "") -> str:
    """Create a JOB_PROCESSING execution and dispatch it to the worker queue.

    Returns the created execution id. Mirrors the ``process_job`` endpoint so a
    job created with ``queue=true`` follows the exact same instant processing
    workflow (create execution → mark queued → enqueue TaskIQ task).
    """
    from processing.domain.enums import ExecutionType
    from processing.application.use_cases.create_processing_execution import (
        CreateProcessingExecutionRequest,
        CreateProcessingExecutionUseCase,
    )
    from processing.application.services.dispatch_processing_execution import (
        DispatchProcessingExecutionService,
    )

    use_case = CreateProcessingExecutionUseCase(exec_repo)
    request = CreateProcessingExecutionRequest(
        execution_type=ExecutionType.JOB_PROCESSING,
        target_type="job",
        target_id=job_id,
        user_id=user_id,
    )
    response = use_case.execute(request)
    DispatchProcessingExecutionService(exec_repo).dispatch(response.execution_id)
    return response.execution_id


@router.post("", status_code=http_status.HTTP_201_CREATED, response_model=CreateJobResponse)
def create_job(
    body: CreateJobRequest,
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
    company_repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    application_repo: SQLAlchemyApplicationRepository = Depends(get_application_repo),
    analysis_repo: SQLAlchemyJobAnalysisRepository = Depends(get_job_analysis_repo),
):
    """Create a new job from a job posting URL.

    When ``body.queue`` is true the job is created and immediately queued for
    processing (the same workflow triggered by ``POST /api/jobs/{id}/process``).
    Otherwise the job is created with status ``imported`` and stays idle.
    """
    existing = find_duplicate_job(repo, body.job_post_url)
    if existing:
        existing_id = existing.get("id")
        recommendations = analysis_repo.recommendations_by_job_ids([existing_id])
        raise JobAlreadyExistsError(
            job_id=existing_id,
            job=_job_summary(
                existing,
                rank=repo.score_rank(existing_id),
                company_type=_linked_company_type(existing, company_repo),
                tracking_status=application_repo.statuses_by_job_ids([existing_id]).get(
                    existing_id
                ),
                recommendation=recommendations.get(existing_id),
            ),
        )

    links_json = json.dumps([l.model_dump() for l in body.links], ensure_ascii=False)
    notes_json = json.dumps([n.model_dump() for n in body.notes], ensure_ascii=False)

    job = repo.create_job(
        url=body.job_post_url,
        title=body.job_title,
        notes=notes_json,
        links=links_json,
    )

    if body.queue:
        execution_id = _queue_job_for_processing(job["id"], exec_repo, user_id=repo._user_id)
        return CreateJobResponse(id=job["id"], status="queued", execution_id=execution_id)

    return CreateJobResponse(id=job["id"], status=job["status"])


def _parse_string_list(raw: Any) -> list[str]:
    """Parse a stored JSON-array column (work_types / employment_types) into a list.

    Tolerates the formats produced over time: JSON arrays, JSON scalars, and
    plain non-JSON strings (legacy corrupt rows). Filters out values that are
    not strings.
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return [raw.strip()] if raw.strip() else []
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
        return [str(parsed).strip()] if str(parsed).strip() else []
    return []


def _normalize_filter_values(raw: list[str] | None, allowed: set[str]) -> list[str] | None:
    """Validate and flatten a multi-value filter param into a clean list.

    Accepts repeated query params (FastAPI list) and/or comma-separated
    values, drops empty pieces, and rejects any value outside ``allowed``
    with a 422 (consistent with the previous single-value pattern check).
    Returns ``None`` when nothing valid was supplied.
    """
    if not raw:
        return None
    items: list[str] = []
    for part in raw:
        for piece in part.split(","):
            piece = piece.strip()
            if not piece:
                continue
            if piece not in allowed:
                raise HTTPException(
                    status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Invalid filter value: {piece}",
                )
            items.append(piece)
    return items or None


def _job_summary(
    job: dict[str, Any],
    rank: int | None = None,
    company_type: str | None = None,
    tracking_status: str | None = None,
    recommendation: str | None = None,
) -> dict[str, Any]:
    """Build a compact summary of an existing job for the duplicate error.

    Mirrors the top-of-detail header (scores + identity rows) so the UI can
    render it below the duplicate error message.
    """
    return {
        "id": job.get("id"),
        "title": job.get("title") or job.get("role"),
        "company": job.get("company"),
        "company_id": job.get("company_id"),
        "company_type": company_type,
        "location": job.get("location"),
        "visa": job.get("visa"),
        "salary": job.get("salary"),
        "employment_types": _parse_string_list(job.get("employment_types")),
        "work_types": _parse_string_list(job.get("work_types")),
        "overall_score": job.get("overall_score"),
        "fit_score": job.get("fit_score"),
        "success_score": job.get("success_score"),
        "rank": rank,
        "tracking_status": tracking_status,
        "recommendation": recommendation,
        "url": job.get("url"),
        "updated_at": job.get("updated_at"),
    }


def _parse_items(raw: Any, plain_key: str = "content") -> list[dict[str, Any]]:
    """Parse a stored notes/links value into a list of item dicts.

    Tolerates the formats produced over time: JSON arrays (Edit Job API),
    JSON scalars, and plain non-JSON strings (legacy worker). Plain strings
    are wrapped under ``plain_key`` so they are never silently dropped.
    """
    if not raw:
        return []
    if isinstance(raw, list):
        return _items_to_dicts(raw, plain_key)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return _items_to_dicts(parsed, plain_key)
            return _items_to_dicts([parsed], plain_key)
        except (TypeError, ValueError):
            return [{plain_key: raw}]
    return []


def _items_to_dicts(items: list[Any], plain_key: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        result.append({plain_key: item} if isinstance(item, str) else item)
    return result


def _v2_job_to_schema(
    job_dict: dict[str, Any],
    latest_execution: dict[str, Any] | None = None,
    recommendation: str | None = None,
    tracking_status: str | None = None,
    rank: int | None = None,
) -> JobListItemSchema:
    scores = ScoresSchema(
        overall=job_dict.get("overall_score"),
        fit=job_dict.get("fit_score"),
        success=job_dict.get("success_score"),
    )
    exec_schema = None
    job_status = None
    if latest_execution:
        exec_schema = ProcessingExecutionSchema(
            id=str(latest_execution.get("id") or job_dict.get("id")),
            status=latest_execution.get("status"),
            started_at=latest_execution.get("started_at"),
            finished_at=latest_execution.get("finished_at"),
        )
        job_status = latest_execution.get("status")
    work_types = [w.lower() for w in _parse_string_list(job_dict.get("work_types"))]
    visa_raw = job_dict.get("visa")
    return JobListItemSchema(
        id=job_dict.get("id"),
        title=job_dict.get("title") or job_dict.get("role"),
        company_name=job_dict.get("company"),
        location=job_dict.get("location"),
        remote="remote" in work_types,
        visa_sponsorship=bool(visa_raw and str(visa_raw).strip()),
        job_status=job_status,
        latest_processing_execution=exec_schema,
        scores=scores,
        recommendation=recommendation,
        pinned=bool(job_dict.get("pinned")),
        dismissed=bool(job_dict.get("dismissed")),
        tags=_parse_string_list(job_dict.get("tags")),
        rank=rank,
        tracking_status=tracking_status,
        easy_apply=bool(job_dict.get("easy_apply")),
        updated_at=job_dict.get("updated_at"),
        created_at=job_dict.get("created_at"),
    )


@router.get("/list", response_model=JobListResponseSchema)
def list_jobs_v2(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    cursor: str | None = Query(None),
    query: str | None = Query(None),
    sort: str = Query("created_at"),
    order: str = Query("desc"),
    processing_status: str | None = Query(None),
    tracking_status: list[str] | None = Query(None),
    company_id: str | None = Query(None),
    location: str | None = Query(None),
    remote: bool | None = Query(None),
    visa: bool | None = Query(None),
    pinned: bool | None = Query(None),
    created_date: str | None = Query(None, pattern="^(today|yesterday|week|month)$"),
    recommendation: list[str] | None = Query(None),
    dismissed: bool | None = Query(None),
    tags: str | None = Query(None),
    overall_score_min: int | None = Query(None),
    overall_score_max: int | None = Query(None),
    fit_score_min: int | None = Query(None),
    fit_score_max: int | None = Query(None),
    success_score_min: int | None = Query(None),
    success_score_max: int | None = Query(None),
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
    analysis_repo: SQLAlchemyJobAnalysisRepository = Depends(get_job_analysis_repo),
    application_repo: SQLAlchemyApplicationRepository = Depends(get_application_repo),
):
    job_ids: list[str] | None = None
    exclude_job_ids: list[str] | None = None
    if processing_status == "none":
        exclude_job_ids = sorted(exec_repo.target_ids("job"))
    elif processing_status:
        job_ids = sorted(exec_repo.target_ids_with_status("job", processing_status))
    tracking_values = _normalize_filter_values(tracking_status, TRACKING_STATUSES)
    if tracking_values:
        specific = [s for s in tracking_values if s != "not_applied"]
        not_applied_selected = "not_applied" in tracking_values
        applied_job_ids = set(application_repo.job_ids_with_application())
        statuses_map = (
            application_repo.statuses_by_job_ids(list(applied_job_ids))
            if applied_job_ids
            else {}
        )
        specific_ids = {jid for jid, st in statuses_map.items() if st in set(specific)}
        matched: set[str] = set(specific_ids)
        if not_applied_selected:
            all_job_ids = {j["id"] for j in repo.get_all_active()}
            matched |= all_job_ids - applied_job_ids
        if job_ids is None:
            job_ids = sorted(matched)
        else:
            job_ids = sorted(set(job_ids) & matched)

    recommendation_values = _normalize_filter_values(
        recommendation, {"apply", "consider", "skip"}
    )
    status_lookup = exec_repo.latest_statuses("job") if sort == "status" else None
    request = ListJobsV2Request(
        page=page, page_size=page_size, cursor=cursor, query=query, sort=sort, order=order,
        job_ids=job_ids,
        exclude_job_ids=exclude_job_ids,
        status_lookup=status_lookup,
        company_id=company_id,
        location=location,
        remote=remote, visa=visa,
        overall_score_min=overall_score_min, overall_score_max=overall_score_max,
        fit_score_min=fit_score_min, fit_score_max=fit_score_max,
        success_score_min=success_score_min, success_score_max=success_score_max,
        pinned=pinned,
        dismissed=dismissed if dismissed is not None else None,
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else None,
        created_date=created_date,
        recommendation=recommendation_values,
    )
    use_case = ListJobsV2UseCase(repo)
    result = use_case.execute(request)
    page_job_ids = [j.get("id") for j in result.items if j.get("id")]
    latest_executions = exec_repo.latest_by_target_ids("job", page_job_ids)
    recommendations = analysis_repo.recommendations_by_job_ids(page_job_ids)
    tracking_statuses = application_repo.statuses_by_job_ids(page_job_ids)
    ranks = repo.ranks_by_ids(page_job_ids)
    items = [
        _v2_job_to_schema(
            j,
            latest_executions.get(j.get("id")),
            recommendations.get(j.get("id")),
            tracking_statuses.get(j.get("id")) or "not_applied",
            ranks.get(j.get("id")),
        )
        for j in result.items
    ]
    total_pages = max(1, math.ceil(result.total / page_size)) if result.total else 1
    return JobListResponseSchema(
        items=items,
        pagination=PaginationSchema(
            page=page, page_size=page_size,
            total_items=result.total, total_pages=total_pages,
        ),
        cursor_pagination=CursorPaginationSchema(
            total_items=result.total,
            next_cursor=result.next_cursor,
            has_more=result.has_more,
        ),
    )


def _step_to_schema(step: Any) -> JobDetailWorkflowStepSchema:
    return JobDetailWorkflowStepSchema(
        id=step.get("id"),
        title=step.get("title"),
        status=step.get("status", "pending"),
        progress=step.get("progress"),
        displayable=step.get("displayable", True),
        children=[_step_to_schema(c) for c in step.get("children", [])],
        error=step.get("error"),
        started_at=step.get("started_at"),
        completed_at=step.get("completed_at"),
    )


def _workflow_to_schema(workflow: Any) -> JobDetailWorkflowSchema | None:
    if not workflow:
        return None
    current_step = workflow.get("current_step")
    return JobDetailWorkflowSchema(
        id=workflow.get("id"),
        name=workflow.get("name", "Job Context Preparation"),
        status=workflow.get("status", "pending"),
        current_step=_step_to_schema(current_step) if current_step else None,
        progress=workflow.get("progress"),
        steps=[_step_to_schema(s) for s in workflow.get("steps", [])],
    )


def _execution_to_schema(execution: Any) -> JobDetailExecutionSchema | None:
    if not execution:
        return None
    workflow = execution.workflow_progress or {}
    current_step = workflow.get("current_step") or {}
    return JobDetailExecutionSchema(
        execution_id=execution.id,
        status=execution.status.value,
        created_at=execution.created_at.isoformat() if execution.created_at else None,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.finished_at.isoformat() if execution.finished_at else None,
        error={"message": execution.error_message} if execution.error_message else None,
        current_step=current_step.get("title") or current_step.get("id"),
        workflow=_workflow_to_schema(workflow),
    )


def _analysis_to_schema(
    analysis: dict | None,
    job_dict: dict[str, Any],
    summary: dict | None,
) -> JobAnalysisBlockSchema | None:
    """Build the analysis block from the canonical row, falling back to the
    legacy jobs/summaries projection for rows processed before the analysis
    phase existed.
    """
    if analysis:
        payload = analysis.get("payload") or {}
        explanation = payload.get("scores_explanation") or {}
        summary_block = payload.get("summary") or {}
        skills = payload.get("skills") or []
        return JobAnalysisBlockSchema(
            recommendation=analysis.get("recommendation"),
            apply_reason=analysis.get("apply_reason") or job_dict.get("apply_reason"),
            scores_explanation=JobAnalysisScoresExplanationSchema(
                fit_factors=explanation.get("fit_factors") or [],
                success_factors=explanation.get("success_factors") or [],
                concerns=explanation.get("concerns") or [],
            ),
            summary=JobAnalysisSummarySchema(
                summary=summary_block.get("summary") or analysis.get("summary") or "",
                resume_fit=summary_block.get("resume_fit") or "",
                note=summary_block.get("note") or "",
            ),
            skills=[JobAnalysisSkillSchema(**s) for s in skills if isinstance(s, dict)],
            insights=payload.get("insights") or [],
            generated_at=analysis.get("generated_at"),
        )

    # Legacy fallback: summarize the projections that exist on the row.
    if job_dict.get("overall_score") is not None or summary:
        return JobAnalysisBlockSchema(
            recommendation=None,
            apply_reason=job_dict.get("apply_reason"),
            scores_explanation=JobAnalysisScoresExplanationSchema(),
            summary=JobAnalysisSummarySchema(
                summary=(summary or {}).get("summary") or "",
                resume_fit=(summary or {}).get("resumeFit") or "",
                note=(summary or {}).get("note") or "",
            ),
            skills=[],
            insights=[],
            generated_at=None,
        )
    return None


def _linked_company_type(
    job_dict: dict[str, Any],
    company_repo: SQLAlchemyCompanyRepository,
) -> str | None:
    """Return the linked company's type for the job detail response."""
    company_id = job_dict.get("company_id")
    if not company_id:
        return None
    company = company_repo.get_by_id(company_id)
    return (company or {}).get("company_type")


def _job_detail_payload(
    job_dict: dict[str, Any],
    latest_execution: Any | None,
    related_companies: list[Any] | None = None,
    company_type: str | None = None,
    rank: int | None = None,
) -> JobDetailResponseSchema:
    """Build the detail response for a freshly read job row."""
    return JobDetailResponseSchema(
        id=job_dict.get("id"),
        title=job_dict.get("title") or job_dict.get("role"),
        company_name=job_dict.get("company"),
        company_id=job_dict.get("company_id"),
        company_type=company_type,
        role=job_dict.get("role"),
        location=job_dict.get("location"),
        work_types=_parse_string_list(job_dict.get("work_types")),
        employment_types=_parse_string_list(job_dict.get("employment_types")),
        salary=job_dict.get("salary"),
        visa=job_dict.get("visa"),
        url=job_dict.get("url"),
        status=job_dict.get("status"),
        rank=rank,
        scores=ScoresSchema(
            overall=job_dict.get("overall_score"),
            fit=job_dict.get("fit_score"),
            success=job_dict.get("success_score"),
        ),
        latest_processing_execution=_execution_to_schema(latest_execution),
        related_companies=related_companies or [],
        dismissed=bool(job_dict.get("dismissed")),
        pinned=bool(job_dict.get("pinned")),
        description=job_dict.get("description"),
        notes=[JobNoteItem(**x) for x in _parse_items(job_dict.get("notes"), plain_key="content")],
        links=[JobLinkItem(**x) for x in _parse_items(job_dict.get("links"), plain_key="url")],
        updated_at=job_dict.get("updated_at"),
        created_at=job_dict.get("created_at"),
        easy_apply=bool(job_dict.get("easy_apply")),
    )


def _related_companies_schema(
    job_id: str,
    job_company_repo: SQLAlchemyJobCompanyRepository,
    company_repo: SQLAlchemyCompanyRepository,
) -> list[Any]:
    """Enrich job_companies rows with company names for the detail response."""
    from jobs.presentation.api.schemas.jobs_v2 import RelatedCompanySchema

    items = job_company_repo.list_by_job(job_id)
    names: dict[str, str | None] = {}
    for row in items:
        company_id = row.get("company_id")
        if company_id and company_id not in names:
            company = company_repo.get_by_id(company_id)
            names[company_id] = (company or {}).get("name")
    return [
        RelatedCompanySchema(
            company_id=row["company_id"],
            name=names.get(row["company_id"]),
            role=row.get("role"),
            company_type=row.get("company_type"),
            confidence=row.get("confidence"),
            reason=row.get("reason"),
        )
        for row in items
    ]


@router.get("/timeline", response_model=JobTimelineResponseSchema)
def get_job_timeline(
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
):
    """Per-day created-job counts, newest first (independent of list filters)."""
    days = repo.count_created_by_day()
    return JobTimelineResponseSchema(days=days, total=sum(d["count"] for d in days))


@router.get("/{job_id}", response_model=JobDetailResponseSchema)
def get_job_detail(
    job_id: str,
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
    analysis_repo: SQLAlchemyJobAnalysisRepository = Depends(get_job_analysis_repo),
    summary_repo: SQLAlchemySummaryRepository = Depends(get_summary_repo),
    job_company_repo: SQLAlchemyJobCompanyRepository = Depends(get_job_company_repo),
    company_repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    application_repo: SQLAlchemyApplicationRepository = Depends(get_application_repo),
):
    job_dict = repo.get_by_id(job_id)
    if not job_dict:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    executions = exec_repo.list_by_target("job", job_id)
    latest_execution = executions[0] if executions else None
    analysis = analysis_repo.get_by_job_id(job_id)
    summary = summary_repo.get_by_job_id(job_id)
    tracking_statuses = application_repo.statuses_by_job_ids([job_id])

    return JobDetailResponseSchema(
        id=job_dict.get("id"),
        title=job_dict.get("title") or job_dict.get("role"),
        company_name=job_dict.get("company"),
        company_id=job_dict.get("company_id"),
        company_type=_linked_company_type(job_dict, company_repo),
        role=job_dict.get("role"),
        location=job_dict.get("location"),
        work_types=_parse_string_list(job_dict.get("work_types")),
        employment_types=_parse_string_list(job_dict.get("employment_types")),
        salary=job_dict.get("salary"),
        visa=job_dict.get("visa"),
        url=job_dict.get("url"),
        status=job_dict.get("status"),
        rank=repo.score_rank(job_id),
        scores=ScoresSchema(
            overall=job_dict.get("overall_score"),
            fit=job_dict.get("fit_score"),
            success=job_dict.get("success_score"),
        ),
        latest_processing_execution=_execution_to_schema(latest_execution),
        analysis=_analysis_to_schema(analysis, job_dict, summary),
        related_companies=_related_companies_schema(job_id, job_company_repo, company_repo),
        description=job_dict.get("description"),
        notes=[JobNoteItem(**x) for x in _parse_items(job_dict.get("notes"), plain_key="content")],
        links=[JobLinkItem(**x) for x in _parse_items(job_dict.get("links"), plain_key="url")],
        tracking_status=tracking_statuses.get(job_id) or "not_applied",
        dismissed=bool(job_dict.get("dismissed")),
        pinned=bool(job_dict.get("pinned")),
        easy_apply=bool(job_dict.get("easy_apply")),
        updated_at=job_dict.get("updated_at"),
        created_at=job_dict.get("created_at"),
    )


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: str,
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
    application_repo: SQLAlchemyApplicationRepository = Depends(get_application_repo),
):
    """Hard-delete a job by UUID and its related tables and executions.

    Application workspace data (applications, follow-ups, documents,
    preparations) belongs to the Applications context and is removed here too
    (logical reference only — the cascade is orchestrated at the API layer).
    """
    job_dict = repo.get_by_id(job_id)
    if not job_dict:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    application_ids = application_repo.list_ids_by_job(job_id)
    application_repo.delete_by_job(job_id)
    for application_id in application_ids:
        exec_repo.delete_by_target("application", application_id)
    exec_repo.delete_by_target("job", job_id)
    if not repo.delete_by_id(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return Response(status_code=204)


@router.patch("/{job_id}", response_model=JobDetailResponseSchema)
def update_job(
    job_id: str,
    body: UpdateJobRequest,
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
    job_company_repo: SQLAlchemyJobCompanyRepository = Depends(get_job_company_repo),
    company_repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
):
    """Partially update a job's core data (Edit Job feature)."""
    data = body.model_dump(exclude_unset=True)
    if "notes" in data and data["notes"] is not None:
        data["notes"] = json.dumps(data["notes"], ensure_ascii=False)
    if "links" in data and data["links"] is not None:
        data["links"] = json.dumps(data["links"], ensure_ascii=False)
    for key in ("work_types", "employment_types"):
        if key in data and data[key] is not None:
            data[key] = json.dumps(data[key], ensure_ascii=False)
    job_dict = repo.update_by_id(job_id, data)
    if not job_dict:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    executions = exec_repo.list_by_target("job", job_id)
    latest_execution = executions[0] if executions else None

    return _job_detail_payload(
        job_dict,
        latest_execution,
        _related_companies_schema(job_id, job_company_repo, company_repo),
        company_type=_linked_company_type(job_dict, company_repo),
        rank=repo.score_rank(job_id),
    )


@router.put("/{job_id}/company", response_model=JobDetailResponseSchema)
def set_job_company(
    job_id: str,
    body: SetJobCompanyRequest,
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    company_repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
    job_company_repo: SQLAlchemyJobCompanyRepository = Depends(get_job_company_repo),
):
    """Link a job to a company (or unlink it by passing company_id=null)."""
    job_dict = repo.get_by_id(job_id)
    if not job_dict:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if body.company_id:
        company = company_repo.get_by_id(body.company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company {body.company_id} not found")
        repo.set_company(job_id, body.company_id, company.get("name") or None)
    else:
        repo.set_company(job_id, None)

    job_dict = repo.get_by_id(job_id)
    executions = exec_repo.list_by_target("job", job_id)
    latest_execution = executions[0] if executions else None
    return _job_detail_payload(
        job_dict,
        latest_execution,
        _related_companies_schema(job_id, job_company_repo, company_repo),
        company_type=_linked_company_type(job_dict, company_repo),
        rank=repo.score_rank(job_id),
    )


@router.put("/{job_id}/pinned")
def set_job_pinned(
    job_id: str,
    body: PinJobRequest,
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
):
    """Set or clear the pinned flag on a job."""
    if not repo.set_pinned(job_id, body.pinned):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"pinned": body.pinned}


@router.put("/{job_id}/dismissed")
def set_job_dismissed(
    job_id: str,
    body: DismissJobRequest,
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
):
    """Set or clear the dismissed flag on a job. When a note is provided and
    the job is being dismissed, the note is appended to the job's notes."""
    job_dict = repo.get_by_id(job_id)
    if not job_dict:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if not repo.set_dismissed(job_id, body.dismissed):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if body.dismissed and body.note and body.note.strip():
        notes = _parse_items(job_dict.get("notes"), plain_key="content")
        notes.append({"content": body.note.strip()})
        repo.update_by_id(job_id, {"notes": json.dumps(notes, ensure_ascii=False)})
    return {"dismissed": body.dismissed}


@router.put("/{job_id}/tags")
def set_job_tags(
    job_id: str,
    body: SetJobTagsRequest,
    repo: SQLAlchemyJobRepository = Depends(get_job_repo),
):
    """Set tags on a job. Replaces the existing tags."""
    if not repo.get_by_id(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if not repo.set_tags(job_id, body.tags):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"tags": body.tags}
