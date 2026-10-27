"""Tests for the Dashboard tracking-status distribution API."""

from __future__ import annotations

import uuid

from applications.infrastructure.models.application_model import ApplicationModel
from jobs.infrastructure.models.job_model import JobModel


def _create_job(test_db, url: str, user_id: str = "test-user", deleted: int = 0) -> JobModel:
    model = JobModel(
        id=str(uuid.uuid7()),
        url=url,
        status="imported",
        deleted=deleted,
        user_id=user_id,
        workflow_log="[]",
        employment_types=["Full-time"],
        rescoring=0,
    )
    test_db.add(model)
    test_db.commit()
    return model


def _create_application(
    test_db,
    job_id: str,
    status: str,
    user_id: str = "test-user",
) -> ApplicationModel:
    model = ApplicationModel(
        id=str(uuid.uuid7()),
        job_id=job_id,
        status=status,
        user_id=user_id,
    )
    test_db.add(model)
    test_db.commit()
    return model


class TestTrackingStatusDistribution:
    def test_counts_every_job_and_keeps_application_statuses(self, client, test_db):
        for index in range(3):
            _create_job(test_db, f"https://example.com/no-application-{index}")
        for status in (
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
        ):
            job = _create_job(test_db, f"https://example.com/{status}")
            _create_application(test_db, job.id, status)

        body = client.get("/api/jobs/tracking-status/distribution").json()

        assert body["total"] == 13
        assert body["items"] == [
            {"status": "not_applied", "count": 3},
            {"status": "seen", "count": 1},
            {"status": "preparing", "count": 1},
            {"status": "ready_to_apply", "count": 1},
            {"status": "applied", "count": 1},
            {"status": "interview", "count": 1},
            {"status": "offer", "count": 1},
            {"status": "accepted", "count": 1},
            {"status": "rejected", "count": 1},
            {"status": "withdrawn", "count": 1},
            {"status": "expired", "count": 1},
        ]

    def test_excludes_deleted_and_other_user_jobs_and_applications(self, client, test_db):
        _create_job(test_db, "https://example.com/kept")
        leaked_application = _create_job(test_db, "https://example.com/leaked-app")
        _create_application(test_db, leaked_application.id, "applied", user_id="other-user")
        _create_job(test_db, "https://example.com/deleted", deleted=1)
        other_job = _create_job(test_db, "https://example.com/other", user_id="other-user")
        _create_application(test_db, other_job.id, "interview", user_id="other-user")

        body = client.get("/api/jobs/tracking-status/distribution").json()

        assert body["total"] == 2
        assert body["items"] == [{"status": "not_applied", "count": 2}]

    def test_empty_dataset(self, client):
        body = client.get("/api/jobs/tracking-status/distribution").json()

        assert body == {"items": [], "total": 0}
