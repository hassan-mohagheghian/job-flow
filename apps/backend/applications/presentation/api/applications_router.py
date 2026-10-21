"""Applications API router — the Job Application Workspace backend.

Owned by the Applications bounded context (per-context router, rule 10). Reads
and writes application records and dispatches generation executions (tailored
resume, cover letter, AI roadmap) through the processing pipeline.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status as http_status
from fastapi import Response
from fastapi.responses import JSONResponse, Response as _FastAPIResponse

from applications.application.services.application_service import ApplicationService
from applications.application.services.document_service import DocumentService
from applications.application.services.follow_up_service import FollowUpService
from applications.application.services.note_service import NoteService
from applications.application.services.status_event_service import StatusEventService
from applications.domain.entities.application import ApplicationStatus, DocumentType
from applications.infrastructure import (
    SQLAlchemyApplicationRepository,
    SQLAlchemyDocumentRepository,
    SQLAlchemyFollowUpRepository,
    SQLAlchemyNoteRepository,
    SQLAlchemyStatusEventRepository,
)
from applications.presentation.api.schemas.applications import (
    ApplicationDetailResponse,
    ApplicationDocumentSchema,
    ApplicationFollowUpSchema,
    ApplicationNoteSchema,
    ApplicationStatusDistributionResponse,
    ApplicationStatusEventSchema,
    CreateApplicationRequest,
    CreateFollowUpRequest,
    CreateNoteRequest,
    DeleteResponse,
    GenerateResponse,
    UpdateApplicationRequest,
    UpdateDocumentRequest,
    UpdateFollowUpRequest,
    UpdateStatusEventRequest,
    build_detail_response,
)
from dependencies import (
    get_application_repo,
    get_application_service,
    get_document_repo,
    get_document_service,
    get_follow_up_repo,
    get_follow_up_service,
    get_note_repo,
    get_note_service,
    get_placeholder_service,
    get_processing_execution_repo,
    get_status_event_repo,
    get_status_event_service,
)
from processing.application.services.dispatch_processing_execution import (
    DispatchProcessingExecutionService,
)
from processing.application.use_cases.create_processing_execution import (
    CreateProcessingExecutionRequest,
    CreateProcessingExecutionUseCase,
)
from processing.domain.enums import ExecutionType
from processing.infrastructure import SQLAlchemyProcessingExecutionRepository
from shared.application.exceptions import BadRequestError, NotFoundError

router = APIRouter()

_EXECUTION_TYPE_BY_DOCUMENT = {
    DocumentType.TAILORED_RESUME: ExecutionType.APPLICATION_RESUME,
    DocumentType.COVER_LETTER: ExecutionType.APPLICATION_COVER_LETTER,
}


def _fill_documents(
    documents: list[dict],
    placeholder_service,
) -> list[dict]:
    """Substitute ``{{placeholder}}`` tokens in each document's content."""
    if not placeholder_service:
        return documents
    return [{**d, "content": placeholder_service.fill(d.get("content") or "")} for d in documents]


def _detail(
    application_repo: SQLAlchemyApplicationRepository,
    follow_up_repo: SQLAlchemyFollowUpRepository,
    document_repo: SQLAlchemyDocumentRepository,
    status_event_repo: SQLAlchemyStatusEventRepository,
    application_id: str,
    placeholder_service=None,
    note_repo: SQLAlchemyNoteRepository | None = None,
) -> ApplicationDetailResponse:
    application = application_repo.get_by_id(application_id)
    if not application:
        raise NotFoundError(f"Application {application_id} not found")
    return build_detail_response(
        application,
        follow_up_repo.list_for_application(application_id),
        _fill_documents(document_repo.list_for_application(application_id), placeholder_service),
        status_event_repo.list_for_application(application_id),
        notes=note_repo.list_for_application(application_id) if note_repo else None,
    )


def _dispatch(exec_repo: SQLAlchemyProcessingExecutionRepository, execution_type: ExecutionType, application_id: str, user_id: str = "") -> str:
    use_case = CreateProcessingExecutionUseCase(exec_repo)
    request = CreateProcessingExecutionRequest(
        execution_type=execution_type,
        target_type="application",
        target_id=application_id,
        user_id=user_id,
    )
    response = use_case.execute(request)
    DispatchProcessingExecutionService(exec_repo).dispatch(response.execution_id)
    return response.execution_id


@router.get(
    "/status-distribution",
    response_model=ApplicationStatusDistributionResponse,
)
def get_status_distribution(
    application_repo: SQLAlchemyApplicationRepository = Depends(get_application_repo),
):
    """Per-status counts of the current user's applications (Dashboard)."""
    return application_repo.status_distribution()


@router.get("/by-job/{job_id}", response_model=ApplicationDetailResponse)
def get_application_by_job(
    job_id: str,
    application_repo: SQLAlchemyApplicationRepository = Depends(get_application_repo),
    follow_up_repo: SQLAlchemyFollowUpRepository = Depends(get_follow_up_repo),
    document_repo: SQLAlchemyDocumentRepository = Depends(get_document_repo),
    status_event_repo: SQLAlchemyStatusEventRepository = Depends(get_status_event_repo),
    note_repo: SQLAlchemyNoteRepository = Depends(get_note_repo),
    placeholder_service=Depends(get_placeholder_service),
):
    application = application_repo.get_by_job_id(job_id)
    if not application:
        raise NotFoundError(f"No application found for job {job_id}")
    return build_detail_response(
        application,
        follow_up_repo.list_for_application(application["id"]),
        _fill_documents(document_repo.list_for_application(application["id"]), placeholder_service),
        status_event_repo.list_for_application(application["id"]),
        notes=note_repo.list_for_application(application["id"]),
    )


@router.post("", status_code=http_status.HTTP_201_CREATED, response_model=ApplicationDetailResponse)
def create_application(
    body: CreateApplicationRequest,
    service: ApplicationService = Depends(get_application_service),
    follow_up_repo: SQLAlchemyFollowUpRepository = Depends(get_follow_up_repo),
    document_repo: SQLAlchemyDocumentRepository = Depends(get_document_repo),
    status_event_repo: SQLAlchemyStatusEventRepository = Depends(get_status_event_repo),
    note_repo: SQLAlchemyNoteRepository = Depends(get_note_repo),
    placeholder_service=Depends(get_placeholder_service),
):
    stored = service.create(body.job_id, seen_at=body.seen_at)
    return build_detail_response(
        stored,
        follow_up_repo.list_for_application(stored["id"]),
        _fill_documents(document_repo.list_for_application(stored["id"]), placeholder_service),
        status_event_repo.list_for_application(stored["id"]),
        notes=note_repo.list_for_application(stored["id"]),
    )


@router.patch("/{application_id}", response_model=ApplicationDetailResponse)
def update_application(
    application_id: str,
    body: UpdateApplicationRequest,
    service: ApplicationService = Depends(get_application_service),
    application_repo: SQLAlchemyApplicationRepository = Depends(get_application_repo),
    follow_up_repo: SQLAlchemyFollowUpRepository = Depends(get_follow_up_repo),
    document_repo: SQLAlchemyDocumentRepository = Depends(get_document_repo),
    status_event_repo: SQLAlchemyStatusEventRepository = Depends(get_status_event_repo),
    note_repo: SQLAlchemyNoteRepository = Depends(get_note_repo),
    placeholder_service=Depends(get_placeholder_service),
):
    data = body.model_dump(exclude_unset=True)
    service.update(application_id, data)
    return _detail(
        application_repo,
        follow_up_repo,
        document_repo,
        status_event_repo,
        application_id,
        placeholder_service,
        note_repo=note_repo,
    )


@router.patch("/timeline/{event_id}", response_model=ApplicationStatusEventSchema)
def update_status_event(
    event_id: str,
    body: UpdateStatusEventRequest,
    service: StatusEventService = Depends(get_status_event_service),
):
    return service.update_changed_at(event_id, body.changed_at or "")


@router.delete("/timeline/{event_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_status_event(
    event_id: str,
    service: StatusEventService = Depends(get_status_event_service),
):
    service.delete(event_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post("/{application_id}/follow-ups", status_code=http_status.HTTP_201_CREATED, response_model=ApplicationFollowUpSchema)
def add_follow_up(
    application_id: str,
    body: CreateFollowUpRequest,
    service: FollowUpService = Depends(get_follow_up_service),
):
    return service.add(application_id, body.scheduled_at, body.note)


@router.patch("/follow-ups/{follow_up_id}", response_model=ApplicationFollowUpSchema)
def update_follow_up(
    follow_up_id: str,
    body: UpdateFollowUpRequest,
    service: FollowUpService = Depends(get_follow_up_service),
):
    data = body.model_dump(exclude_unset=True)
    return service.update(
        follow_up_id,
        scheduled_at=data.get("scheduled_at"),
        note=data.get("note"),
        completed=data.get("completed"),
    )


@router.delete("/follow-ups/{follow_up_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_follow_up(
    follow_up_id: str,
    service: FollowUpService = Depends(get_follow_up_service),
):
    service.delete(follow_up_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post("/{application_id}/notes", status_code=http_status.HTTP_201_CREATED, response_model=ApplicationNoteSchema)
def add_note(
    application_id: str,
    body: CreateNoteRequest,
    service: NoteService = Depends(get_note_service),
):
    return service.add(application_id, body.content)


@router.delete("/notes/{note_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    service: NoteService = Depends(get_note_service),
):
    service.delete(note_id)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post("/{application_id}/roadmap/generate", status_code=http_status.HTTP_202_ACCEPTED, response_model=GenerateResponse)
def generate_roadmap(
    application_id: str,
    application_repo: SQLAlchemyApplicationRepository = Depends(get_application_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    if not application_repo.get_by_id(application_id):
        raise NotFoundError(f"Application {application_id} not found")
    execution_id = _dispatch(exec_repo, ExecutionType.ROADMAP_GENERATION, application_id, user_id=application_repo._user_id)
    return GenerateResponse(execution_id=execution_id, status="queued", artifact="roadmap")


@router.post("/{application_id}/documents/{document_type}/generate", status_code=http_status.HTTP_202_ACCEPTED, response_model=GenerateResponse)
def generate_document(
    application_id: str,
    document_type: str,
    application_repo: SQLAlchemyApplicationRepository = Depends(get_application_repo),
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    if document_type not in DocumentType.ALL:
        raise BadRequestError(
            f"Invalid document type '{document_type}'; allowed: {', '.join(DocumentType.ALL)}"
        )
    if not application_repo.get_by_id(application_id):
        raise NotFoundError(f"Application {application_id} not found")
    execution_id = _dispatch(exec_repo, _EXECUTION_TYPE_BY_DOCUMENT[document_type], application_id, user_id=application_repo._user_id)
    return GenerateResponse(execution_id=execution_id, status="queued", artifact=document_type)


@router.patch("/documents/{document_id}", response_model=ApplicationDocumentSchema)
def update_document(
    document_id: str,
    body: UpdateDocumentRequest,
    service: DocumentService = Depends(get_document_service),
):
    return service.update_content(document_id, body.content)


@router.delete("/documents/{document_id}", status_code=http_status.HTTP_200_OK, response_model=DeleteResponse)
def delete_document(
    document_id: str,
    service: DocumentService = Depends(get_document_service),
):
    service.delete(document_id)
    return DeleteResponse(status="deleted")


@router.get("/documents/{document_id}/pdf")
def download_document_pdf(
    document_id: str,
    document_repo: SQLAlchemyDocumentRepository = Depends(get_document_repo),
    placeholder_service=Depends(get_placeholder_service),
):
    """Export a generated document as a PDF with placeholders filled in.

    Returns a binary ``application/pdf`` response so the frontend can save it
    directly as a file download.
    """
    from shared.infrastructure.pdf_renderer import MarkdownPdfRenderer

    document = document_repo.get_by_id(document_id)
    if not document:
        raise NotFoundError(f"Document {document_id} not found")
    content = placeholder_service.fill(document.get("content") or "")
    document_type = document.get("document_type") or "document"
    filename = f"{document_type}-v{document.get('version') or 1}.pdf"
    pdf_bytes = MarkdownPdfRenderer().render(content, title=document_type.replace("_", " ").title())
    return _FastAPIResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
