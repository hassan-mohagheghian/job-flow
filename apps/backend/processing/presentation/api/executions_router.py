"""ProcessingExecution REST + SSE API.

- GET  /api/processing/executions                → list executions
- GET  /api/processing/executions/{id}           → get one execution (with workflow progress)
- POST /api/processing/executions/{id}/start     → start a queued execution
- POST /api/processing/executions/{id}/cancel    → cancel a queued/running execution
- POST /api/processing/executions/{id}/retry     → retry a failed execution
- GET  /api/processing/queue                     → Processing Queue snapshot
- DELETE /api/processing/queue/{execution_id}    → remove a queue entry
- GET  /api/processing/{execution_id}/events     → SSE stream for one execution

The API does not expose TaskIQ or LangGraph internals to clients.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from dependencies import get_company_repo, get_processing_execution_repo, get_job_repo
from companies.infrastructure import SQLAlchemyCompanyRepository
from jobs.infrastructure import SQLAlchemyJobRepository
from processing.infrastructure import SQLAlchemyProcessingExecutionRepository
from processing.application.services.processing_queue_service import ProcessingQueueService
from processing.application.services.execution_actions import ExecutionActionService
from shared.application.exceptions import NotFoundError
from shared.infrastructure.events.processing_events import execution_channel
from shared.infrastructure.events.sse import stream_channel
from shared.infrastructure.config.app_config import SSE_KEEPALIVE_SECONDS

router = APIRouter()


def _execution_detail(execution) -> dict[str, Any]:
    workflow = execution.workflow_progress or {}
    current_step = workflow.get("current_step")
    return {
        "execution_id": execution.id,
        "job_id": execution.target_id if execution.target_type == "job" else None,
        "status": execution.status.value,
        "created_at": execution.created_at.isoformat() if execution.created_at else None,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.finished_at.isoformat() if execution.finished_at else None,
        "error": {"message": execution.error_message} if execution.error_message else None,
        "current_step": current_step,
        "workflow": workflow or None,
    }


@router.get("/executions")
def list_executions(
    limit: int = 50,
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    executions = exec_repo.list_recent(limit=limit)
    return [_execution_detail(e) for e in executions]


@router.get("/executions/{execution_id}")
def get_execution(
    execution_id: str,
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    execution = exec_repo.get_by_id(execution_id)
    if not execution:
        raise NotFoundError(f"ProcessingExecution {execution_id} not found")
    return _execution_detail(execution)


@router.post("/executions/{execution_id}/start")
def start_execution(
    execution_id: str,
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    return ExecutionActionService(exec_repo).start(execution_id)


@router.post("/executions/{execution_id}/cancel")
def cancel_execution(
    execution_id: str,
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    return ExecutionActionService(exec_repo).cancel(execution_id)


@router.post("/executions/{execution_id}/retry")
def retry_execution(
    execution_id: str,
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    existing = exec_repo.get_by_id(execution_id)
    return ExecutionActionService(exec_repo, user_id=existing.user_id if existing else "").retry(execution_id)


@router.get("/queue")
def get_queue(
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
    job_repo: SQLAlchemyJobRepository = Depends(get_job_repo),
    company_repo: SQLAlchemyCompanyRepository = Depends(get_company_repo),
):
    return ProcessingQueueService(exec_repo, job_repo, company_repo).snapshot()


@router.delete("/queue/{execution_id}")
def remove_queue_entry(
    execution_id: str,
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    return ExecutionActionService(exec_repo).remove_queue_entry(execution_id)


@router.get("/{execution_id}/events")
async def execution_events(
    execution_id: str,
    request: Request,
    exec_repo: SQLAlchemyProcessingExecutionRepository = Depends(get_processing_execution_repo),
):
    execution = exec_repo.get_by_id(execution_id)
    if not execution:
        raise NotFoundError(f"ProcessingExecution {execution_id} not found")

    channel = execution_channel(execution_id)

    async def event_stream():
        async for chunk in stream_channel(channel):
            if await request.is_disconnected():
                break
            yield chunk
        # Keep the connection open for late events
        while not await request.is_disconnected():
            await asyncio.sleep(SSE_KEEPALIVE_SECONDS)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        # `no-transform` forbids intermediaries from compressing the stream
        # (compression buffers SSE frames — see the global events router).
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
