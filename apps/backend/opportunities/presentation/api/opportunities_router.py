"""Opportunities API router — the inbound-opportunity pipeline backend.

Owned by the Opportunities bounded context (per-context router, rule 10).
Processing is synchronous in phase one: ``process`` / ``reprocess`` run
extract → resolve → evaluate inline and return the updated detail.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from fastapi import status as http_status

from dependencies import get_opportunity_service
from auth.presentation.api.auth_router import get_current_user
from auth.domain.user import User
from opportunities.application.services.opportunity_service import (
    OpportunityPipelineError,
    OpportunityService,
)
from opportunities.presentation.api.schemas.opportunities import (
    CreateNoteRequest,
    CreateOpportunityRequest,
    DismissOpportunityRequest,
    OpportunityDetailResponse,
    OpportunityListResponse,
    OpportunityNoteSchema,
    UpdateOpportunityLinksRequest,
    UpdateOpportunityStatusRequest,
    build_detail_response,
    build_list_item,
)
from shared.application.exceptions import ExternalServiceError

router = APIRouter()


def _detail(service: OpportunityService, opportunity_id: str, duplicate: bool = False) -> OpportunityDetailResponse:
    detail = service.get_detail(opportunity_id)
    return build_detail_response(
        detail, detail.get("evaluations"), duplicate=duplicate, notes=detail.get("notes")
    )


@router.post("", response_model=OpportunityDetailResponse, status_code=http_status.HTTP_201_CREATED)
def create_opportunity(
    body: CreateOpportunityRequest,
    service: OpportunityService = Depends(get_opportunity_service),
):
    from fastapi.responses import JSONResponse

    stored, duplicate = service.create_manual(body.model_dump())
    detail = _detail(service, stored["id"], duplicate)
    if duplicate:
        return JSONResponse(status_code=http_status.HTTP_200_OK, content=detail.model_dump())
    return detail


@router.get("", response_model=OpportunityListResponse)
def list_opportunities(
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    query: str | None = Query(default=None),
    dismissed: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: OpportunityService = Depends(get_opportunity_service),
):
    items, total = service.list(
        status=status, source=source, query=query, limit=limit, offset=offset,
        dismissed=dismissed,
    )
    return OpportunityListResponse(items=[build_list_item(i) for i in items], total=total)


@router.get("/{opportunity_id}", response_model=OpportunityDetailResponse)
def get_opportunity(
    opportunity_id: str,
    service: OpportunityService = Depends(get_opportunity_service),
):
    return _detail(service, opportunity_id)


def _run_pipeline(service: OpportunityService, opportunity_id: str, reprocess: bool = False) -> OpportunityDetailResponse:
    try:
        detail = service.reprocess(opportunity_id) if reprocess else service.process(opportunity_id)
    except OpportunityPipelineError as exc:
        raise ExternalServiceError(str(exc)) from exc
    return build_detail_response(detail, detail.get("evaluations"), notes=detail.get("notes"))


@router.post("/{opportunity_id}/process", response_model=OpportunityDetailResponse)
def process_opportunity(
    opportunity_id: str,
    service: OpportunityService = Depends(get_opportunity_service),
):
    return _run_pipeline(service, opportunity_id)


@router.post("/{opportunity_id}/reprocess", response_model=OpportunityDetailResponse)
def reprocess_opportunity(
    opportunity_id: str,
    service: OpportunityService = Depends(get_opportunity_service),
):
    return _run_pipeline(service, opportunity_id, reprocess=True)


@router.patch("/{opportunity_id}/links", response_model=OpportunityDetailResponse)
def update_opportunity_links(
    opportunity_id: str,
    body: UpdateOpportunityLinksRequest,
    service: OpportunityService = Depends(get_opportunity_service),
):
    stored = service.set_links(opportunity_id, job_id=body.job_id, company_id=body.company_id)
    return _detail(service, stored["id"])


@router.patch("/{opportunity_id}/status", response_model=OpportunityDetailResponse)
def update_opportunity_status(
    opportunity_id: str,
    body: UpdateOpportunityStatusRequest,
    service: OpportunityService = Depends(get_opportunity_service),
):
    stored = service.set_status(opportunity_id, body.status)
    return _detail(service, stored["id"])


@router.delete("/{opportunity_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_opportunity(
    opportunity_id: str,
    service: OpportunityService = Depends(get_opportunity_service),
):
    service.delete(opportunity_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post("/{opportunity_id}/notes", status_code=http_status.HTTP_201_CREATED, response_model=OpportunityNoteSchema)
def add_note(
    opportunity_id: str,
    body: CreateNoteRequest,
    service: OpportunityService = Depends(get_opportunity_service),
    current_user: User = Depends(get_current_user),
):
    return service.add_note(
        opportunity_id,
        title=body.title,
        content=body.content,
        author=current_user.display_name,
    )


@router.delete("/notes/{note_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    service: OpportunityService = Depends(get_opportunity_service),
):
    service.delete_note(note_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.put("/{opportunity_id}/dismissed", response_model=OpportunityDetailResponse)
def set_opportunity_dismissed(
    opportunity_id: str,
    body: DismissOpportunityRequest,
    service: OpportunityService = Depends(get_opportunity_service),
    current_user: User = Depends(get_current_user),
):
    """Dismiss or undismiss an opportunity. When a note is provided while
    dismissing, it is recorded as a follow-up note titled ``Dismissed``."""
    stored = service.set_dismissed(
        opportunity_id,
        body.dismissed,
        note=body.note,
        author=current_user.display_name,
    )
    return _detail(service, stored["id"])
