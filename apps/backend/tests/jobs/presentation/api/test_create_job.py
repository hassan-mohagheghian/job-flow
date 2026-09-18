"""Tests for POST /api/jobs (Add Job Drawer) including the queue flag."""

from unittest.mock import patch

from jobs.infrastructure.models.job_model import JobModel
from jobs.infrastructure.models.job_analysis_model import JobAnalysisModel
from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel


def _count_executions(test_db, job_id: str) -> int:
    return test_db.query(ProcessingExecutionModel).filter(
        ProcessingExecutionModel.target_type == "job",
        ProcessingExecutionModel.target_id == job_id,
    ).count()


def test_create_job_returns_201_imported(client, test_db):
    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync") as publish,
    ):
        response = client.post(
            "/api/jobs",
            json={
                "job_post_url": "https://example.com/jobs/backend-engineer",
                "job_title": "Backend Engineer",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "imported"
    assert data["execution_id"] is None

    job = test_db.query(JobModel).filter(JobModel.id == data["id"]).first()
    assert job is not None
    assert job.title == "Backend Engineer"
    assert job.status == "imported"
    assert _count_executions(test_db, job.id) == 0
    enqueue.assert_not_called()
    publish.assert_not_called()


def test_create_job_with_links_and_notes(client, test_db):
    response = client.post(
        "/api/jobs",
        json={
            "job_post_url": "https://example.com/jobs/senior-python",
            "links": [
                {"title": "LinkedIn", "url": "https://linkedin.com/jobs/view/123"},
            ],
            "notes": [
                {"title": "Requirements", "content": "Python 3.14 experience"},
            ],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "imported"

    job = test_db.query(JobModel).filter(JobModel.id == data["id"]).first()
    assert '"url": "https://linkedin.com/jobs/view/123"' in job.links
    assert "Python 3.14 experience" in job.notes


def test_create_and_queue_dispatches_instant_workflow(client, test_db):
    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync") as publish,
    ):
        response = client.post(
            "/api/jobs",
            json={
                "job_post_url": "https://example.com/jobs/queue-me",
                "job_title": "Queue Me",
                "queue": True,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "queued"
    assert data["execution_id"] is not None

    execution = test_db.query(ProcessingExecutionModel).filter(
        ProcessingExecutionModel.id == data["execution_id"]
    ).first()
    assert execution is not None
    assert execution.target_type == "job"
    assert execution.target_id == data["id"]
    assert execution.status == "queued"

    enqueue.assert_called_once_with(data["execution_id"])
    publish.assert_called_once()


def test_create_with_queue_defaults_false(client, test_db):
    with patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue:
        response = client.post(
            "/api/jobs",
            json={"job_post_url": "https://example.com/jobs/no-queue"},
        )

    assert response.status_code == 201
    assert response.json()["status"] == "imported"
    enqueue.assert_not_called()


def test_create_same_non_linkedin_url_twice_succeeds(client, test_db):
    """Non-LinkedIn URLs are not restricted until their own rule exists."""
    url = "https://example.com/jobs/duplicate"
    with patch("shared.infrastructure.taskiq.client.enqueue_execution_sync"):
        first = client.post("/api/jobs", json={"job_post_url": url})
        assert first.status_code == 201

    second = client.post("/api/jobs", json={"job_post_url": url, "queue": True})
    assert second.status_code == 201


def test_create_duplicate_linkedin_job_returns_409(client, test_db):
    """Same LinkedIn job id with different tracking params is a duplicate."""
    first_url = (
        "https://www.linkedin.com/jobs/view/4333938709/?trackingId=AAA&refId=BBB"
    )
    second_url = (
        "https://www.linkedin.com/jobs/view/4333938709/"
        "?trackingId=CCC%3D%3D&refId=DDD%3D%3D&eBP=NON_CHARGEABLE_CHANNEL"
    )
    with patch("shared.infrastructure.taskiq.client.enqueue_execution_sync"):
        first = client.post("/api/jobs", json={"job_post_url": first_url})
        assert first.status_code == 201

    second = client.post("/api/jobs", json={"job_post_url": second_url, "queue": True})
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["code"] == "JOB_ALREADY_EXISTS"
    assert body["error"]["message"] == "A Job with the same primary URL already exists."
    assert body["error"]["details"]["job_id"] == first.json()["id"]
    assert body["error"]["details"]["job"]["id"] == first.json()["id"]


def test_create_duplicate_job_includes_recommendation(client, test_db):
    """The duplicate error response includes the recommendation from job analysis."""
    url = "https://www.linkedin.com/jobs/view/5555555555/"
    with patch("shared.infrastructure.taskiq.client.enqueue_execution_sync"):
        first = client.post("/api/jobs", json={"job_post_url": url})
        assert first.status_code == 201

    job_id = first.json()["id"]
    analysis = JobAnalysisModel(
        job_id=job_id, recommendation="apply", payload=None, user_id="test-user"
    )
    test_db.add(analysis)
    test_db.commit()

    second = client.post("/api/jobs", json={"job_post_url": url})
    assert second.status_code == 409
    body = second.json()
    assert body["error"]["details"]["job"]["recommendation"] == "apply"


def test_create_linkedin_different_job_ids_succeed(client, test_db):
    with patch("shared.infrastructure.taskiq.client.enqueue_execution_sync"):
        first = client.post(
            "/api/jobs",
            json={"job_post_url": "https://www.linkedin.com/jobs/view/11111/"},
        )
        assert first.status_code == 201

    second = client.post(
        "/api/jobs",
        json={"job_post_url": "https://www.linkedin.com/jobs/view/22222/?trackingId=Z"},
    )
    assert second.status_code == 201


def test_create_job_missing_url_returns_422(client):
    response = client.post("/api/jobs", json={"job_title": "No URL"})
    assert response.status_code == 422
