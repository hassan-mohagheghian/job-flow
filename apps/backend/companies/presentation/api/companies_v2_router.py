"""Companies API router — list, detail, create, update, delete, notes, links.

The single companies router: it owns the paginated ``/companies/list`` route,
the all-in-one detail payload, and the CRUD / notes / links / reprocess
endpoints. There is no legacy companies router anymore.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, UTC
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from fastapi.responses import Response

from companies.application.services.company_service import CompanyService
from companies.domain.company_type import normalize_company_type
from companies.infrastructure import SQLAlchemyCompanyRepository
from companies.infrastructure.repositories.sa_company_intelligence_repository import (
    SQLAlchemyCompanyIntelligenceRepository,
)
from companies.infrastructure.repositories.sa_company_link_repository import (
    SQLAlchemyCompanyLinkRepository,
)
from companies.presentation.api.schemas.companies_v2 import (
    CompanyCreateLinkItem,
    CompanyCreateNoteItem,
    CompanyCreateRequest,
    CompanyCreateResponse,
    CompanyDetailResponseSchema,
    CompanyExecutionSchema,
    CompanyIntelligenceSchema,
    CompanyJobRefSchema,
    CompanyLinkItemSchema,
    CompanyLinkRequest,
    CompanyListResponseSchema,
    CompanyListItemSchema,
    CompanyMainRef,
    CompanyMainRequest,
    CompanyNoteRequest,
    CompanyNoteSchema,
    CompanyPinRequest,
    CompanyProcessingSchema,
    CompanyScoresSchema,
    CompanyUpdateRequest,
    RecruiterForSchema,
    RecruiterJobRefSchema,
)
from dependencies import (
    get_company_intelligence_repo,
    get_company_link_repo,
    get_company_repo,
    get_job_company_repo,
    get_job_repo,
    get_processing_execution_repo,
)
from jobs.infrastructure.repositories.sa_job_company_repository import SQLAlchemyJobCompanyRepository
from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
from processing.infrastructure import SQLAlchemyProcessingExecutionRepository
from shared.application.exceptions import NotFoundError

router = APIRouter()

DEFAULT_PAGE_SIZE = 25

SORTABLE_SCORE_FIELDS = ("overall_score", "fit_score", "success_score")

# Multi-column tiebreak order for score sorts (primary first) so rows tied on
# the primary score are ordered deterministically.
SCORE_TIEBREAK_KEYS = {
    "overall_score": ("overall", "success", "fit"),
    "fit_score": ("fit", "overall", "success"),
    "success_score": ("success", "overall", "fit"),
}


def _queue_company_for_processing(company_id: str, exec_repo, user_id: str = "") -> str:
    """Create a COMPANY_PROCESSING execution and dispatch it to the worker queue.

    Mirrors the job intake flow: create execution → mark queued → enqueue TaskIQ.
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
        execution_type=ExecutionType.COMPANY_PROCESSING,
        target_type="company",
        target_id=company_id,
        user_id=user_id,
    )
    response = use_case.execute(request)
    DispatchProcessingExecutionService(exec_repo).dispatch(response.execution_id)
    return response.execution_id


def _cursor_decode(cursor: str) -> int:
    """Decode an opaque base64 offset cursor; invalid cursors restart at 0."""
    if not cursor:
        return 0
    try:
        return int(base64.b64decode(cursor.encode()).decode())
    except Exception:
        return 0


def _cursor_encode(offset: int) -> str:
    return base64.b64encode(str(offset).encode()).decode()


def _matches(
    row: dict[str, Any],
    query: str,
    industry: str,
    pinned: bool | None = None,
    status: str | None = None,
    status_lookup: dict[str, str] | None = None,
    company_type: str | None = None,
) -> bool:
    if pinned is not None and bool(row.get("pinned")) != pinned:
        return False
    if status:
        row_status = (status_lookup or {}).get(row.get("id"))
        if status == "none":
            if row_status is not None:
                return False
        elif row_status != status:
            return False
    if query:
        q = query.lower()
        haystacks = [
            row.get("name"),
            row.get("industry"),
            row.get("city"),
            row.get("country"),
            row.get("description"),
        ]
        if not any(h and q in str(h).lower() for h in haystacks):
            return False
    if industry:
        if (row.get("industry") or "") != industry:
            return False
    if company_type:
        if (row.get("company_type") or "") != company_type:
            return False
    return True


def _sort_key(row: dict[str, Any], sort: str, order: str) -> Any:
    if sort in SORTABLE_SCORE_FIELDS:
        scores = row.get("_scores") or {}
        keys = SCORE_TIEBREAK_KEYS[sort]
        primary = scores.get(keys[0])
        if primary is None:
            return None
        # Direction-aware NULL sentinel keeps NULLS LAST in both directions
        # when the whole tuple is compared with reverse=(order == "desc").
        sentinel = -1 if order == "desc" else 10_000
        return tuple(v if v is not None else sentinel for v in (scores.get(k) for k in keys))
    if sort == "name":
        return (row.get("name") or "").lower()
    if sort == "job_count":
        return row.get("job_count") or 0
    if sort == "updated_at":
        return row.get("updated_at")
    return row.get("created_at")


def _to_list_item(
    row: dict[str, Any],
    execution: dict[str, Any] | None = None,
    name_by_id: dict[str, str] | None = None,
    alias_counts: dict[str, int] | None = None,
    recruiter_job_counts: dict[str, int] | None = None,
) -> CompanyListItemSchema:
    scores = row.get("_scores") or {}
    exec_schema = None
    if execution:
        exec_schema = CompanyExecutionSchema(
            id=str(execution.get("id") or row.get("id")),
            status=execution.get("status"),
            started_at=execution.get("started_at"),
            finished_at=execution.get("finished_at"),
        )
    parent_company_id = row.get("parent_company_id")
    main_company = None
    if parent_company_id:
        main_name = (name_by_id or {}).get(parent_company_id)
        if main_name is not None:
            main_company = CompanyMainRef(id=parent_company_id, name=main_name)
    return CompanyListItemSchema(
        id=row["id"],
        name=row.get("name") or "",
        industry=row.get("industry"),
        city=row.get("city"),
        country=row.get("country"),
        company_size=row.get("company_size"),
        company_type=row.get("company_type"),
        logo_url=row.get("logo_url"),
        website=row.get("website"),
        description=row.get("description"),
        job_count=row.get("job_count", 0),
        recruiter_job_count=(recruiter_job_counts or {}).get(row["id"], 0),
        scores=CompanyScoresSchema(
            overall=scores.get("overall"),
            fit=scores.get("fit"),
            success=scores.get("success"),
            overall_grade=scores.get("overall_grade") or scores.get("fit_grade"),
        ),
        processing=CompanyProcessingSchema(
            status=execution.get("status") if execution else None,
            current_node=row.get("current_node"),
            progress_pct=row.get("progress_pct"),
            error=row.get("error"),
        ),
        latest_processing_execution=exec_schema,
        parent_company_id=parent_company_id,
        main_company=main_company,
        alias_count=(alias_counts or {}).get(row["id"], 0),
        is_alias=bool(parent_company_id),
        pinned=bool(row.get("pinned")),
        updated_at=row.get("updated_at"),
        created_at=row.get("created_at"),
    )


@router.get("/list")
def list_companies_v2(
    query: str = Query("", description="Substring search over name, industry, city, country, description"),
    industry: str = Query("", description="Exact industry filter"),
    company_type: str = Query("", description="Exact company type filter (e.g. PRODUCT_COMPANY, RECRUITING_AGENCY)"),
    pinned: bool | None = Query(None, description="Only include pinned companies"),
    status: str | None = Query(None, description="Exact company processing status filter"),
    sort: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", description="asc or desc"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=200),
    cursor: str = Query("", description="Opaque pagination cursor"),
    repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
    job_company_repo: SQLAlchemyJobCompanyRepository = Depends(get_job_company_repo),
) -> CompanyListResponseSchema:
    """List companies with server-side search, filter, sort and cursor pagination."""
    status_lookup = exec_repo.latest_statuses("company")
    rows = [r for r in repo.list_all_with_details() if _matches(r, query, industry, pinned, status, status_lookup, company_type)]

    key: Callable[[dict[str, Any]], Any] = lambda r: _sort_key(r, sort, order)
    with_value = [r for r in rows if key(r) is not None]
    without_value = [r for r in rows if key(r) is None]
    with_value.sort(key=key, reverse=(order == "desc"))
    rows = with_value + without_value

    total = len(rows)
    offset = _cursor_decode(cursor)
    page = rows[offset:offset + page_size]
    next_offset = offset + len(page)
    has_more = next_offset < total

    name_by_id = {r.get("id"): (r.get("name") or "") for r in rows if r.get("id")}
    alias_counts: dict[str, int] = {}
    for r in rows:
        parent = r.get("parent_company_id")
        if parent:
            alias_counts[parent] = alias_counts.get(parent, 0) + 1

    page_ids = [r.get("id") for r in page if r.get("id")]
    latest_executions = exec_repo.latest_by_target_ids("company", page_ids)
    recruiter_job_counts = job_company_repo.recruiter_job_counts(page_ids)

    return CompanyListResponseSchema(
        items=[
            _to_list_item(
                r,
                latest_executions.get(r.get("id")),
                name_by_id,
                alias_counts,
                recruiter_job_counts,
            )
            for r in page
        ],
        next_cursor=_cursor_encode(next_offset) if has_more else None,
        has_more=has_more,
        total_items=total,
    )


def _parse_json_field(value: Any) -> Any:
    """Best-effort JSON parse of a stored Text column value."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _scores_from_intelligence(intel: dict[str, Any] | None) -> CompanyScoresSchema | None:
    if not intel:
        return None
    scores = _parse_json_field(intel.get("scores")) or {}
    if not isinstance(scores, dict):
        scores = {}
    return CompanyScoresSchema(
        overall=scores.get("overall"),
        fit=scores.get("fit"),
        success=scores.get("success"),
        overall_grade=scores.get("overall_grade") or scores.get("fit_grade"),
    )


def _to_intelligence_schema(intel: dict[str, Any] | None) -> CompanyIntelligenceSchema | None:
    if not intel:
        return None
    return CompanyIntelligenceSchema(
        overview=_parse_json_field(intel.get("overview")),
        culture_analysis=_parse_json_field(intel.get("culture_analysis")),
        international_analysis=_parse_json_field(intel.get("international_analysis")),
        career_analysis=_parse_json_field(intel.get("career_analysis")),
        benefits_analysis=_parse_json_field(intel.get("benefits_analysis")),
        visa_analysis=_parse_json_field(intel.get("visa_analysis")),
        technology_analysis=_parse_json_field(intel.get("technology_analysis")),
        recommendation=_parse_json_field(intel.get("recommendation")),
        scores=_parse_json_field(intel.get("scores")) or None,
        generated_at=intel.get("generated_at"),
    )


@router.get("/{id}", response_model=CompanyDetailResponseSchema)
def get_company_detail(
    id: str,
    repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    intel_repo: SQLAlchemyCompanyIntelligenceRepository = Depends(get_company_intelligence_repo),
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
    job_repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    job_company_repo: SQLAlchemyJobCompanyRepository = Depends(get_job_company_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
) -> CompanyDetailResponseSchema:
    """Get a company by id with all related data in a single payload."""
    return _build_company_detail(id, repo, intel_repo, link_repo, job_repo, job_company_repo, exec_repo)


def _build_company_detail(
    id: str,
    repo: SQLAlchemyCompanyRepository,
    intel_repo: SQLAlchemyCompanyIntelligenceRepository,
    link_repo: SQLAlchemyCompanyLinkRepository,
    job_repo: SQLAlchemyJobRepository,
    job_company_repo: SQLAlchemyJobCompanyRepository,
    exec_repo: SQLAlchemyProcessingExecutionRepository,
) -> CompanyDetailResponseSchema:
    company = repo.get_by_id(id)
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {id} not found")

    intel = intel_repo.get_by_company_id(id)
    links = link_repo.get_by_company_id(id)
    jobs = job_repo.get_jobs_by_company_id(id)
    company_job_ranks = job_repo.ranks_by_ids([j["id"] for j in jobs])
    latest_execution = exec_repo.latest_by_target_ids("company", [id]).get(id)

    parent_company_id = company.get("parent_company_id")
    main_company = None
    if parent_company_id:
        parent = repo.get_by_id(parent_company_id)
        if parent:
            main_company = CompanyMainRef(id=parent_company_id, name=parent.get("name") or "")

    notes = [
        CompanyNoteSchema(id=l["id"], content=l.get("title", "").removeprefix("note:"), created_at=l.get("created_at"))
        for l in links
        if l.get("title", "").startswith("note:")
    ]
    links_schema = [
        CompanyLinkItemSchema(
            id=l["id"],
            url=l.get("url"),
            title=l.get("title"),
            description=l.get("description"),
            status=l.get("status"),
            created_at=l.get("created_at"),
        )
        for l in links
        if not l.get("title", "").startswith("note:")
    ]
    jobs_schema = [
        CompanyJobRefSchema(
            id=j["id"],
            role=j.get("role"),
            location=j.get("location"),
            match=j.get("match"),
            score=j.get("score"),
            fit_score=j.get("fit_score"),
            success_score=j.get("success_score"),
            overall_score=j.get("overall_score"),
            rank=company_job_ranks.get(j["id"]),
        )
        for j in jobs
    ]

    hiring_pairs = job_company_repo.recruiter_hiring_pairs(id)
    jobs_by_hiring_company: dict[str, list[str]] = {}
    for pair in hiring_pairs:
        hiring_company_id = pair.get("hiring_company_id")
        if hiring_company_id:
            jobs_by_hiring_company.setdefault(hiring_company_id, []).append(pair.get("job_id"))

    all_job_ids = [job_id for job_ids in jobs_by_hiring_company.values() for job_id in job_ids]
    job_by_id = {j["id"]: j for j in job_repo.get_jobs_by_ids(all_job_ids)}
    recruiter_for = [
        RecruiterForSchema(
            company_id=hiring_company_id,
            name=(repo.get_by_id(hiring_company_id) or {}).get("name"),
            job_count=len(job_ids),
            jobs=[
                RecruiterJobRefSchema(
                    id=job_id,
                    title=(job_by_id.get(job_id) or {}).get("title"),
                    location=(job_by_id.get(job_id) or {}).get("location"),
                )
                for job_id in sorted(
                    job_ids,
                    key=lambda jid: (job_by_id.get(jid) or {}).get("title") or "",
                )
            ],
        )
        for hiring_company_id, job_ids in sorted(
            jobs_by_hiring_company.items(), key=lambda item: len(item[1]), reverse=True
        )
    ]

    # Client jobs this recruiter published, excluding jobs where it is also the
    # hiring company (its own role). A job with an unknown hiring company still
    # counts — the recruiter published it for a client.
    recruiter_rows = job_company_repo.list_by_company(id, role="recruiter")
    self_hiring_job_ids = {
        r["job_id"] for r in job_company_repo.list_by_company(id, role="hiring")
    }
    recruiter_job_ids = [
        r["job_id"] for r in recruiter_rows if r["job_id"] not in self_hiring_job_ids
    ]
    recruiter_job_by_id = {
        j["id"]: j for j in job_repo.get_jobs_by_ids(recruiter_job_ids)
    }
    recruiter_job_ranks = job_repo.ranks_by_ids(recruiter_job_ids)
    recruiter_jobs = sorted(
        (
            CompanyJobRefSchema(
                id=j["id"],
                role=j.get("role") or j.get("title"),
                location=j.get("location"),
                match=j.get("match"),
                score=j.get("score"),
                fit_score=j.get("fit_score"),
                success_score=j.get("success_score"),
                overall_score=j.get("overall_score"),
                rank=recruiter_job_ranks.get(j["id"]),
            )
            for j in recruiter_job_by_id.values()
        ),
        key=lambda ref: (ref.role or "") or "",
    )

    return CompanyDetailResponseSchema(
        id=company["id"],
        name=company.get("name") or "",
        website=company.get("website"),
        domain=company.get("domain"),
        industry=company.get("industry"),
        country=company.get("country"),
        city=company.get("city"),
        description=company.get("description"),
        company_size=company.get("company_size"),
        company_type=company.get("company_type"),
        logo_url=company.get("logo_url"),
        founded_year=company.get("founded_year"),
        job_count=len(jobs_schema),
        status=latest_execution.get("status") if latest_execution else None,
        current_node=company.get("current_node"),
        progress_pct=company.get("progress_pct"),
        error=company.get("error"),
        notes=notes,
        links=links_schema,
        intelligence=_to_intelligence_schema(intel),
        scores=_scores_from_intelligence(intel),
        jobs=jobs_schema,
        recruiter_job_count=len(recruiter_jobs),
        recruiter_for=recruiter_for,
        recruiter_jobs=recruiter_jobs,
        parent_company_id=parent_company_id,
        main_company=main_company,
        alias_count=repo.count_aliases(id),
        is_alias=bool(parent_company_id),
        pinned=bool(company.get("pinned")),
        created_at=company.get("created_at"),
        updated_at=company.get("updated_at"),
    )


@router.put("/{id}/pinned")
def set_company_pinned(
    id: str,
    body: CompanyPinRequest,
    repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
):
    """Set or clear the pinned flag on a company."""
    if not repo.set_pinned(id, body.pinned):
        raise HTTPException(status_code=404, detail=f"Company {id} not found")
    return {"id": id, "pinned": body.pinned}


@router.put("/{id}/main", response_model=CompanyDetailResponseSchema)
def relate_company_main(
    id: str,
    body: CompanyMainRequest,
    repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    intel_repo: SQLAlchemyCompanyIntelligenceRepository = Depends(get_company_intelligence_repo),
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
    job_repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    job_company_repo: SQLAlchemyJobCompanyRepository = Depends(get_job_company_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
) -> CompanyDetailResponseSchema:
    """Relate a company to a main company (null clears the relation).

    Relating re-points the jobs of the company (and its own aliases) onto the
    main company, so the main stays the single reference for the work.
    """
    from companies.application.services.company_relation_service import CompanyRelationService

    service = CompanyRelationService(repo)
    result = service.relate(id, body.main_company_id) if body.main_company_id else service.unrelate(id)

    for affected_id in result.get("affected_company_ids", []):
        job_repo.reassign_company(affected_id, result["main_company_id"])

    return _build_company_detail(id, repo, intel_repo, link_repo, job_repo, job_company_repo, exec_repo)


# ── Create / Update / Delete ──────────────────────────────────────


@router.post("", status_code=http_status.HTTP_201_CREATED, response_model=CompanyCreateResponse, response_model_exclude_none=True)
def create_company(
    body: CompanyCreateRequest,
    repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    intel_repo: SQLAlchemyCompanyIntelligenceRepository = Depends(get_company_intelligence_repo),
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
) -> CompanyCreateResponse:
    """Create a company from intake (name + notes + links).

    When ``body.queue`` is true (default) the company is created and immediately
    queued for processing through the COMPANY_PROCESSING execution lifecycle.
    """
    service = CompanyService(repo, intel_repo, link_repo)
    company = service.create_from_intake(
        name=body.name,
        notes=[n.model_dump() if isinstance(n, CompanyCreateNoteItem) else dict(n) for n in body.notes]
        if body.notes else [],
        links=[l.model_dump() if isinstance(l, CompanyCreateLinkItem) else str(l) for l in body.links]
        if body.links else [],
        source=body.source,
        input_type=body.input_type,
    )
    execution_id = None
    if body.queue:
        execution_id = _queue_company_for_processing(company["id"], exec_repo, user_id=repo._user_id)
        company["status"] = "queued"
    return CompanyCreateResponse(
        id=company["id"],
        name=company.get("name") or "",
        source=company.get("source"),
        input_type=company.get("input_type"),
        status=company.get("status") or "created",
        execution_id=execution_id,
        created_at=company.get("created_at"),
        updated_at=company.get("updated_at"),
    )


@router.put("/{id}", response_model=CompanyDetailResponseSchema)
def update_company(
    id: str,
    body: CompanyUpdateRequest,
    repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    intel_repo: SQLAlchemyCompanyIntelligenceRepository = Depends(get_company_intelligence_repo),
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
    job_repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    job_company_repo: SQLAlchemyJobCompanyRepository = Depends(get_job_company_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
) -> CompanyDetailResponseSchema:
    """Update a company and return its full detail payload."""
    data = {k: getattr(body, k) for k in body.model_fields_set}
    if "company_type" in data:
        data["company_type"] = normalize_company_type(data["company_type"])
    updated = repo.update(id, data)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Company {id} not found")
    return _build_company_detail(id, repo, intel_repo, link_repo, job_repo, job_company_repo, exec_repo)


@router.delete("/{id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_company(
    id: str,
    repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    intel_repo: SQLAlchemyCompanyIntelligenceRepository = Depends(get_company_intelligence_repo),
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
) -> Response:
    """Hard-delete a company and its related tables and executions."""
    company = repo.get_by_id(id)
    if not company:
        raise NotFoundError(f"Company {id} not found")
    exec_repo.delete_by_target("company", id)
    link_repo.delete_by_company_id(id)
    intel_repo.delete_by_company_id(id)
    if not repo.delete(id):
        raise NotFoundError(f"Company {id} not found")
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post("/{id}/reprocess")
def reprocess_company(
    id: str,
    repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    """Queue a company for reprocessing through the execution lifecycle."""
    from processing.application.services.execution_actions import ExecutionActionService

    company = repo.get_by_id(id)
    if not company:
        return {"error": "Not found"}

    result = ExecutionActionService(exec_repo, user_id=repo._user_id).reprocess("company", id)
    repo.update_fields(id, status="queued", error=None, updated_at=datetime.now(UTC).isoformat())
    return {"status": "queued", "execution_id": result["execution_id"]}


# ── Notes ─────────────────────────────────────────────────────────


def _notes_from_links(links: list[dict[str, Any]]) -> list[CompanyNoteSchema]:
    return [
        CompanyNoteSchema(id=l["id"], content=l.get("title", "").removeprefix("note:"), created_at=l.get("created_at"))
        for l in links
        if l.get("title", "").startswith("note:")
    ]


@router.get("/{id}/notes")
def get_company_notes(
    id: str,
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
) -> list[CompanyNoteSchema]:
    """Get all notes for a company."""
    return _notes_from_links(link_repo.get_by_company_id(id))


@router.post("/{id}/notes", status_code=http_status.HTTP_201_CREATED)
def add_company_note(
    id: str,
    body: CompanyNoteRequest,
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
) -> CompanyNoteSchema:
    """Add a note to a company (stored as a ``note:`` link row)."""
    link = link_repo.create(id, "", f"note:{body.content}")
    return CompanyNoteSchema(id=link["id"], content=body.content, created_at=link.get("created_at"))


@router.put("/{id}/notes/{note_id}")
def update_company_note(
    id: str,
    note_id: int,
    body: CompanyNoteRequest,
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
) -> CompanyNoteSchema:
    """Update a company note."""
    link = link_repo.update(note_id, id, "", f"note:{body.content}")
    if not link:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found")
    return CompanyNoteSchema(id=link["id"], content=body.content, created_at=link.get("created_at"))


@router.delete("/{id}/notes/{note_id}")
def delete_company_note(
    id: str,
    note_id: int,
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
) -> dict[str, str]:
    """Delete a company note."""
    link_repo.delete(note_id, id)
    return {"status": "deleted"}


# ── Links ─────────────────────────────────────────────────────────


@router.post("/{id}/links", status_code=http_status.HTTP_201_CREATED)
def add_company_link(
    id: str,
    body: CompanyLinkRequest,
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
) -> dict[str, Any]:
    """Add a link to a company."""
    return link_repo.create(id, body.url, body.title or "", body.description or "")


@router.put("/{id}/links/{link_id}")
def update_company_link(
    id: str,
    link_id: int,
    body: CompanyLinkRequest,
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
) -> dict[str, Any]:
    """Update a company link."""
    link = link_repo.update(link_id, id, body.url, body.title or "", body.description or "")
    if not link:
        raise HTTPException(status_code=404, detail=f"Link {link_id} not found")
    return link


@router.delete("/{id}/links/{link_id}")
def delete_company_link(
    id: str,
    link_id: int,
    link_repo: SQLAlchemyCompanyLinkRepository = Depends(get_company_link_repo),
) -> dict[str, str]:
    """Delete a company link."""
    link_repo.delete(link_id, id)
    return {"status": "deleted"}
