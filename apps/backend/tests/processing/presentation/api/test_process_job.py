from datetime import datetime, UTC
from unittest.mock import patch

import uuid

from jobs.infrastructure.models.job_model import JobModel
from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel


def _seed_job(sa_session, **extra) -> str:
    job = JobModel(
        id=str(uuid.uuid7()),
        url="https://example.com/job/1",
        title="Software Engineer",
        company="Tech Corp",
        location="Berlin",
        deleted=0,
        workflow_log="[]",
        work_types=["Remote"],
        employment_types=["Full-time"],
        rescoring=0,
        user_id="test-user",
        **extra,
    )
    sa_session.add(job)
    sa_session.commit()
    return job.id


def _seed_execution(sa_session, job_id: str, status: str) -> ProcessingExecutionModel:
    execution = ProcessingExecutionModel(
        id=str(uuid.uuid4()),
        execution_type="job_processing",
        status=status,
        target_type="job",
        target_id=job_id,
        created_at=datetime.now(UTC),
    )
    sa_session.add(execution)
    sa_session.commit()
    return execution


def test_process_job_returns_202(client, sa_session):
    job_id = _seed_job(sa_session)

    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync") as publish,
    ):
        response = client.post(f"/api/jobs/{job_id}/process")

    assert response.status_code == 202
    data = response.json()
    assert "execution_id" in data
    assert data["status"] == "queued"
    enqueue.assert_called_once_with(data["execution_id"])
    publish.assert_called_once()


def test_process_job_returns_404_when_not_found(client):
    response = client.post("/api/jobs/999/process")
    assert response.status_code == 404


def test_process_job_replaces_failed_execution(client, sa_session):
    job_id = _seed_job(sa_session)
    failed = _seed_execution(sa_session, job_id, "failed")

    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync"),
    ):
        response = client.post(f"/api/jobs/{job_id}/process")

    assert response.status_code == 202
    data = response.json()
    assert data["execution_id"] != failed.id

    sa_session.expire_all()
    old = sa_session.get(ProcessingExecutionModel, failed.id)
    assert old.status == "cancelled"

    snapshot = client.get("/api/processing/queue").json()
    assert all(
        entry["execution_id"] != failed.id
        for section in snapshot.values()
        for entry in section
    )


def test_process_job_is_conflict_when_already_active(client, sa_session):
    job_id = _seed_job(sa_session)
    _seed_execution(sa_session, job_id, "queued")

    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync") as publish,
    ):
        response = client.post(f"/api/jobs/{job_id}/process")

    assert response.status_code == 409
    enqueue.assert_not_called()
    publish.assert_not_called()


def test_process_job_allows_new_execution_after_completed(client, sa_session):
    job_id = _seed_job(sa_session)
    _seed_execution(sa_session, job_id, "completed")

    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync") as publish,
    ):
        response = client.post(f"/api/jobs/{job_id}/process")

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    enqueue.assert_called_once_with(data["execution_id"])
    publish.assert_called_once()
