"""Worker-side ProcessingExecution runner.

Drives a ProcessingExecution through its lifecycle by coordinating the
LangGraph workflow execution:

    Load ProcessingExecution
        ↓
    Mark execution running
        ↓
    Start LangGraph workflow
        ↓
    Update workflow progress after each node
        ↓
    Complete or fail execution

TaskIQ starts this runner (via process_execution_task). The runner updates
ProcessingExecution state and publishes processing events for SSE delivery.
"""

from __future__ import annotations

import threading
from datetime import datetime, UTC

from processing.application.workflows import progress_ops
from processing.domain.enums import ExecutionStatus, ExecutionType
from processing.infrastructure.repositories.sa_processing_execution_repository import (
    SQLAlchemyProcessingExecutionRepository,
)
from shared.infrastructure.database.session import get_session_sync
from shared.infrastructure.events import processing_events
from shared.infrastructure.process.logging_config import get_logger

log = get_logger("processing.runner")

HEARTBEAT_INTERVAL_SECONDS = 30


class ProcessingExecutionRunner:
    """Executes a ProcessingExecution and updates its lifecycle state."""

    def __init__(self, repository=None, job_repository=None):
        self._repository = repository
        self._job_repository = job_repository

    @staticmethod
    def _should_reuse(has_content: bool, latest_prior_status) -> bool:
        """Reuse previously prepared (fetched/extracted) content on a reprocess
        only when the target already has persisted content AND the most recent
        prior execution failed (an LLM/analysis failure). A first process or a
        reprocess of a completed target must run from scratch."""
        return bool(has_content) and latest_prior_status == ExecutionStatus.FAILED

    def _reuse_available(self, execution, session) -> bool:
        """Whether the current run may reuse already-fetched content.

        True only for job/company targets that already have persisted prepared
        content whose most recent prior execution FAILED (i.e. it failed at the
        LLM/analysis step, so fetching again would be wasteful).
        """
        target_type = execution.target_type
        if target_type not in ("job", "company"):
            return False
        try:
            has_content = bool(self._target_content(execution, session).strip())
        except Exception:
            has_content = False
        try:
            exec_repo = self._repository or SQLAlchemyProcessingExecutionRepository(session)
            prior = [
                e for e in exec_repo.list_by_target(target_type, execution.target_id)
                if e.id != execution.id
            ]
        except Exception:
            prior = []
        if not prior:
            return False
        latest = max(prior, key=lambda e: e.created_at or "")
        return self._should_reuse(has_content, latest.status)

    @staticmethod
    def _start_heartbeat(
        execution_id: str,
        repo_factory,
        stop_event: threading.Event,
    ) -> threading.Thread:
        """Start a daemon thread that updates heartbeat_at periodically."""
        def _heartbeat_loop():
            while not stop_event.wait(HEARTBEAT_INTERVAL_SECONDS):
                try:
                    session = repo_factory()
                    try:
                        repo = SQLAlchemyProcessingExecutionRepository(session)
                        execution = repo.get_by_id(execution_id)
                        if execution and execution.status == ExecutionStatus.RUNNING:
                            execution.heartbeat_at = datetime.now(UTC)
                            repo.save(execution)
                    finally:
                        session.close()
                except Exception:
                    log.debug(
                        "processing.heartbeat.write_failed",
                        execution_id=execution_id,
                    )

        thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        thread.start()
        return thread

    @staticmethod
    def _target_content(execution, session) -> str:
        """Return the target's persisted prepared content (combined text)."""
        if execution.target_type == "job":
            from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository

            row = SQLAlchemyJobRepository(session).get_by_id(execution.target_id) or {}
            return str(row.get("raw_description") or row.get("description") or "")
        if execution.target_type == "company":
            from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository

            row = SQLAlchemyCompanyRepository(session).get_by_id(execution.target_id) or {}
            return str(row.get("raw_content") or "")
        return ""

    def run(self, execution_id: str) -> dict:
        session = None
        heartbeat_stop = threading.Event()
        heartbeat_thread = None
        try:
            if self._repository is not None:
                repo = self._repository
                job_repo = self._job_repository
            else:
                session = get_session_sync()
                repo = SQLAlchemyProcessingExecutionRepository(session)
                job_repo = None
            execution = repo.get_by_id(execution_id)
            if not execution:
                log.warning("processing.execution.not_found", execution_id=execution_id)
                return {"status": "skipped", "execution_id": execution_id}

            job_id = self._job_id(execution)
            started_at = datetime.now(UTC)

            execution.status = ExecutionStatus.RUNNING
            execution.started_at = started_at
            execution.heartbeat_at = started_at
            execution.workflow_progress = progress_ops.build_initial_progress(
                execution.id, execution.target_type
            ).to_dict()
            repo.save(execution)
            processing_events.publish_sync(
                processing_events.EXECUTION_STARTED,
                execution.id,
                job_id,
                ExecutionStatus.RUNNING.value,
                user_id=execution.user_id,
                target_type=execution.target_type,
                target_id=execution.target_id,
                updated_at=started_at.isoformat(),
            )

            heartbeat_thread = self._start_heartbeat(
                execution_id, get_session_sync, heartbeat_stop,
            )

            try:
                result = self._run_workflow(execution, job_repo, session)
            except Exception as e:
                finished_at = datetime.now(UTC)
                if session is not None:
                    session.rollback()
                execution.status = ExecutionStatus.FAILED
                execution.finished_at = finished_at
                execution.error_message = str(e)
                if execution.workflow_progress:
                    execution.workflow_progress["status"] = "failed"
                repo.save(execution)
                processing_events.publish_sync(
                    processing_events.EXECUTION_FAILED,
                    execution.id,
                    job_id,
                    ExecutionStatus.FAILED.value,
                    user_id=execution.user_id,
                    message=str(e),
                    target_type=execution.target_type,
                    target_id=execution.target_id,
                    updated_at=finished_at.isoformat(),
                )
                log.error("processing.execution.failed", execution_id=execution.id, error=str(e))
                raise

            finished_at = datetime.now(UTC)
            if session is not None:
                session.rollback()
            execution.status = ExecutionStatus.COMPLETED
            execution.finished_at = finished_at
            execution.error_message = None
            if execution.workflow_progress:
                execution.workflow_progress["status"] = "completed"
            repo.save(execution)
            processing_events.publish_sync(
                processing_events.EXECUTION_COMPLETED,
                execution.id,
                job_id,
                ExecutionStatus.COMPLETED.value,
                user_id=execution.user_id,
                target_type=execution.target_type,
                target_id=execution.target_id,
                updated_at=finished_at.isoformat(),
            )
            log.info("processing.execution.completed", execution_id=execution.id)
            return result
        finally:
            heartbeat_stop.set()
            if heartbeat_thread is not None:
                heartbeat_thread.join(timeout=5)
            if session is not None:
                session.close()

    @staticmethod
    def _job_id(execution) -> str | None:
        """Map a processing execution to the job_id used in SSE payloads.

        The new processing features identify jobs by their UUID `id`, so the
        SSE payload carries the job's UUID rather than the numeric `num`.
        """
        if execution.target_type == "job":
            return execution.target_id
        return None

    def _run_workflow(self, execution, job_repo=None, session=None) -> dict:
        """Start the LangGraph workflow matching the execution's type.

        Business logic is not duplicated here — the runner delegates to the
        existing application workers / workflows that own LangGraph execution.

        JOB_PROCESSING executions run the JobContextPreparationGraph (no LLM).
        """
        user_id = getattr(execution, "user_id", "")
        if execution.execution_type == ExecutionType.JOB_PROCESSING:
            from processing.domain.workflow.job_processing_state import JobProcessingState
            from processing.infrastructure.workflow import (
                build_job_analysis_graph,
                build_job_context_preparation_graph,
            )

            graph_session = session
            owns_session = False
            if graph_session is None:
                graph_session = get_session_sync()
                owns_session = True
            try:
                state = JobProcessingState(
                    execution_id=execution.id,
                    job_id=self._job_id(execution) or "",
                    workflow_progress=progress_ops.build_initial_progress(
                        execution.id, execution.target_type
                    ),
                )
                reuse = self._reuse_available(execution, graph_session)
                if reuse:
                    analysis_graph = build_job_analysis_graph(graph_session, user_id=user_id)
                    final = analysis_graph.invoke(state)
                else:
                    graph = build_job_context_preparation_graph(graph_session, user_id=user_id)
                    final = graph.invoke(state)
                    if final.status != ExecutionStatus.FAILED:
                        analysis_graph = build_job_analysis_graph(graph_session, user_id=user_id)
                        final = analysis_graph.invoke(final)
                if final.workflow_progress is not None:
                    execution.workflow_progress = final.workflow_progress.to_dict()
                if final.status == ExecutionStatus.FAILED:
                    raise RuntimeError("; ".join(final.errors) or "Job processing failed")
                return {"job_id": self._job_id(execution)}
            finally:
                if owns_session:
                    graph_session.close()

        if execution.execution_type == ExecutionType.COMPANY_PROCESSING:
            from processing.domain.workflow.company_processing_state import CompanyProcessingState
            from processing.infrastructure.workflow import (
                build_company_analysis_graph,
                build_company_context_preparation_graph,
            )

            graph_session = session
            owns_session = False
            if graph_session is None:
                graph_session = get_session_sync()
                owns_session = True
            try:
                state = CompanyProcessingState(
                    execution_id=execution.id,
                    company_id=execution.target_id,
                    workflow_progress=progress_ops.build_initial_progress(
                        execution.id, execution.target_type
                    ),
                )
                reuse = self._reuse_available(execution, graph_session)
                if reuse:
                    analysis_graph = build_company_analysis_graph(graph_session, user_id=user_id)
                    final = analysis_graph.invoke(state)
                else:
                    graph = build_company_context_preparation_graph(graph_session, user_id=user_id)
                    final = graph.invoke(state)
                    if final.status != ExecutionStatus.FAILED:
                        analysis_graph = build_company_analysis_graph(graph_session, user_id=user_id)
                        final = analysis_graph.invoke(final)
                if final.workflow_progress is not None:
                    execution.workflow_progress = final.workflow_progress.to_dict()
                if final.status == ExecutionStatus.FAILED:
                    raise RuntimeError("; ".join(final.errors) or "Company processing failed")
                return {"company_id": execution.target_id}
            finally:
                if owns_session:
                    graph_session.close()

        if execution.execution_type == ExecutionType.CANDIDATE_PROCESSING:
            from processing.domain.workflow.candidate_processing_state import CandidateProcessingState
            from processing.infrastructure.workflow import (
                build_candidate_processing_graph,
                build_candidate_source_preparation_graph,
            )

            graph_session = session
            owns_session = False
            if graph_session is None:
                graph_session = get_session_sync()
                owns_session = True
            try:
                graph = build_candidate_source_preparation_graph(graph_session, user_id=user_id)
                state = CandidateProcessingState(
                    execution_id=execution.id,
                    profile_id=execution.target_id or "",
                    workflow_progress=progress_ops.build_initial_progress(
                        execution.id, execution.target_type
                    ),
                )
                final = graph.invoke(state)
                if final.status != ExecutionStatus.FAILED:
                    processing_graph = build_candidate_processing_graph(graph_session, user_id=user_id)
                    final = processing_graph.invoke(final)
                if final.workflow_progress is not None:
                    execution.workflow_progress = final.workflow_progress.to_dict()
                if final.status == ExecutionStatus.FAILED:
                    raise RuntimeError("; ".join(final.errors) or "Candidate processing failed")
                return {"profile_id": final.profile_id or execution.target_id}
            finally:
                if owns_session:
                    graph_session.close()

        if execution.execution_type in (
            ExecutionType.APPLICATION_RESUME,
            ExecutionType.APPLICATION_COVER_LETTER,
        ):
            from processing.domain.workflow.application_intelligence_state import (
                ApplicationIntelligenceState,
            )
            from processing.infrastructure.workflow import build_application_intelligence_graph

            graph_session = session
            owns_session = False
            if graph_session is None:
                graph_session = get_session_sync()
                owns_session = True
            try:
                graph = build_application_intelligence_graph(graph_session, user_id=user_id)
                state = ApplicationIntelligenceState(
                    execution_id=execution.id,
                    application_id=execution.target_id,
                    job_id="",
                    intent=execution.execution_type.value,
                    workflow_progress=progress_ops.build_initial_progress(
                        execution.id, execution.target_type
                    ),
                )
                final = graph.invoke(state)
                if final.workflow_progress is not None:
                    execution.workflow_progress = final.workflow_progress.to_dict()
                if final.status == ExecutionStatus.FAILED:
                    raise RuntimeError("; ".join(final.errors) or "Application generation failed")
                return {
                    "application_id": execution.target_id,
                    "persisted_id": final.persisted_id,
                }
            finally:
                if owns_session:
                    graph_session.close()

        if execution.execution_type == ExecutionType.ROADMAP_GENERATION:
            from processing.domain.workflow.roadmap_generation_state import (
                RoadmapGenerationState,
            )
            from processing.infrastructure.workflow import build_roadmap_generation_graph

            graph_session = session
            owns_session = False
            if graph_session is None:
                graph_session = get_session_sync()
                owns_session = True
            try:
                graph = build_roadmap_generation_graph(graph_session, user_id=user_id)
                state = RoadmapGenerationState(
                    execution_id=execution.id,
                    application_id=execution.target_id,
                    job_id="",
                    intent=execution.execution_type.value,
                    workflow_progress=progress_ops.build_initial_progress(
                        execution.id, "roadmap"
                    ),
                )
                final = graph.invoke(state)
                if final.workflow_progress is not None:
                    execution.workflow_progress = final.workflow_progress.to_dict()
                if final.status == ExecutionStatus.FAILED:
                    raise RuntimeError("; ".join(final.errors) or "Roadmap generation failed")
                return {
                    "application_id": execution.target_id,
                    "roadmap_id": final.persisted_roadmap_id,
                }
            finally:
                if owns_session:
                    graph_session.close()

        raise RuntimeError(f"Unsupported execution type: {execution.execution_type}")
