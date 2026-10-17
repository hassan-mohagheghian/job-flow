"""Tests for ProcessingExecution dispatch service and execution runner lifecycle."""

import uuid
from datetime import datetime, UTC
from unittest.mock import patch

import pytest

from processing.domain.enums import ExecutionType, ExecutionStatus
from processing.domain.entities.processing_execution import ProcessingExecution
from processing.application.services.dispatch_processing_execution import DispatchProcessingExecutionService
from processing.infrastructure.runner.execution_runner import ProcessingExecutionRunner
from shared.application.exceptions import NotFoundError


class FakeExecutionRepo:
    def __init__(self):
        self._store: dict[str, ProcessingExecution] = {}

    def save(self, execution: ProcessingExecution) -> ProcessingExecution:
        self._store[execution.id] = execution
        return execution

    def get_by_id(self, execution_id: str) -> ProcessingExecution | None:
        return self._store.get(execution_id)

    def list_by_target(self, target_type: str, target_id: str) -> list[ProcessingExecution]:
        return [e for e in self._store.values() if e.target_type == target_type and e.target_id == target_id]

    def list_recent(self, limit: int = 50) -> list[ProcessingExecution]:
        return list(self._store.values())[:limit]

    def update_status(self, execution_id: str, status: str, **extra) -> bool:
        execution = self._store.get(execution_id)
        if not execution:
            return False
        execution.status = ExecutionStatus(status)
        return True


def _execution(status: ExecutionStatus = ExecutionStatus.CREATED) -> ProcessingExecution:
    return ProcessingExecution(
        id=str(uuid.uuid4()),
        execution_type=ExecutionType.JOB_PROCESSING,
        target_type="job",
        target_id="1",
        status=status,
        created_at=datetime.now(UTC),
    )


class TestDispatchProcessingExecutionService:
    def test_dispatch_marks_queued_and_enqueues(self):
        repo = FakeExecutionRepo()
        execution = _execution()
        repo.save(execution)

        with (
            patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
            patch("shared.infrastructure.events.processing_events.publish_sync") as publish,
        ):
            DispatchProcessingExecutionService(repo).dispatch(execution.id)

        assert execution.status == ExecutionStatus.QUEUED
        enqueue.assert_called_once_with(execution.id)
        publish.assert_called_once()

    def test_dispatch_raises_for_unknown_execution(self):
        repo = FakeExecutionRepo()
        with pytest.raises(NotFoundError):
            DispatchProcessingExecutionService(repo).dispatch("does-not-exist")

    def test_dispatch_raises_when_not_created(self):
        repo = FakeExecutionRepo()
        execution = _execution(status=ExecutionStatus.QUEUED)
        repo.save(execution)
        with pytest.raises(Exception):
            DispatchProcessingExecutionService(repo).dispatch(execution.id)


class TestProcessingExecutionRunner:
    def test_run_completes_execution_and_publishes(self):
        repo = FakeExecutionRepo()
        execution = _execution(status=ExecutionStatus.QUEUED)
        repo.save(execution)

        with (
            patch.object(ProcessingExecutionRunner, "_run_workflow", return_value={"done": True}),
            patch("shared.infrastructure.events.processing_events.publish_sync") as publish,
        ):
            result = ProcessingExecutionRunner(repo).run(execution.id)

        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.started_at is not None
        assert execution.finished_at is not None
        assert result["done"] is True
        names = [call.args[0] for call in publish.call_args_list]
        assert "execution.started" in names
        assert "execution.completed" in names

    def test_run_completion_clears_stale_timeout_error(self):
        """Regression (prompt 222): a workflow that finishes after the
        reconcile sweep already recorded a timeout message must not keep
        that error on a COMPLETED execution."""
        repo = FakeExecutionRepo()
        execution = _execution(status=ExecutionStatus.QUEUED)
        execution.error_message = "Execution timed out after 620s. Check status or retry."
        repo.save(execution)

        with (
            patch.object(ProcessingExecutionRunner, "_run_workflow", return_value={"done": True}),
            patch("shared.infrastructure.events.processing_events.publish_sync"),
        ):
            ProcessingExecutionRunner(repo).run(execution.id)

        assert execution.status == ExecutionStatus.COMPLETED
        assert execution.error_message is None

    def test_run_marks_failed_and_publishes_on_error(self):
        repo = FakeExecutionRepo()
        execution = _execution(status=ExecutionStatus.QUEUED)
        repo.save(execution)

        def boom(*args, **kwargs):
            raise RuntimeError("workflow crashed")

        with (
            patch.object(ProcessingExecutionRunner, "_run_workflow", side_effect=boom),
            patch("shared.infrastructure.events.processing_events.publish_sync") as publish,
        ):
            with pytest.raises(RuntimeError):
                ProcessingExecutionRunner(repo).run(execution.id)

        assert execution.status == ExecutionStatus.FAILED
        assert "workflow crashed" in (execution.error_message or "")
        names = [call.args[0] for call in publish.call_args_list]
        assert "execution.failed" in names


class TestProcessingExecutionRunnerApplication:
    def test_run_workflow_dispatches_application_generation(self):
        from processing.domain.workflow.application_intelligence_state import (
            ApplicationIntelligenceState,
        )

        repo = FakeExecutionRepo()
        execution = ProcessingExecution(
            id=str(uuid.uuid4()),
            execution_type=ExecutionType.APPLICATION_RESUME,
            target_type="application",
            target_id="app-1",
            status=ExecutionStatus.CREATED,
            created_at=datetime.now(UTC),
        )
        repo.save(execution)

        class FakeGraph:
            def invoke(self, state: ApplicationIntelligenceState) -> ApplicationIntelligenceState:
                state.status = ExecutionStatus.COMPLETED
                state.persisted_id = "doc-1"
                return state

        with (
            patch(
                "processing.infrastructure.workflow.build_application_intelligence_graph",
                return_value=FakeGraph(),
            ),
            patch("shared.infrastructure.events.processing_events.publish_sync"),
        ):
            result = ProcessingExecutionRunner(repo).run(execution.id)

        assert result["application_id"] == "app-1"
        assert result["persisted_id"] == "doc-1"


class TestProcessingExecutionRunnerRealSession:
    def test_run_persists_real_error_after_aborted_transaction(self, sa_session):
        """A DB error during the workflow aborts the session transaction; the
        runner must roll back before saving the FAILED state so the real error
        is recorded instead of being masked by InFailedSqlTransaction.
        """
        from sqlalchemy import text

        from processing.infrastructure.models.processing_execution_model import (
            ProcessingExecutionModel,
        )
        from processing.infrastructure.runner.execution_runner import (
            get_session_sync,
            ProcessingExecutionRunner,
        )

        execution = _execution(status=ExecutionStatus.QUEUED)
        model = ProcessingExecutionModel(
            id=execution.id,
            execution_type=ExecutionType.JOB_PROCESSING.value,
            status=ExecutionStatus.QUEUED.value,
            target_type="job",
            target_id="1",
        )
        sa_session.add(model)
        sa_session.commit()

        def boom(*args, **kwargs):
            try:
                sa_session.execute(text("SELECT * FROM nonexistent_trigger_table"))
            except Exception:
                pass
            raise RuntimeError("real node error")

        with (
            patch.object(ProcessingExecutionRunner, "_run_workflow", side_effect=boom),
            patch(
                "processing.infrastructure.runner.execution_runner.get_session_sync",
                return_value=sa_session,
            ),
        ):
            with pytest.raises(RuntimeError, match="real node error"):
                ProcessingExecutionRunner().run(execution.id)

        row = (
            sa_session.query(ProcessingExecutionModel)
            .filter(ProcessingExecutionModel.id == execution.id)
            .first()
        )
        assert row is not None
        assert row.status == ExecutionStatus.FAILED.value
        assert row.error_message == "real node error"
