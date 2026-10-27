"""Tests for the Delete Job API (DELETE /api/jobs/{job_id})."""

from jobs.infrastructure.models.job_model import JobModel
from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel


"""Tests for the Delete Job API (DELETE /api/jobs/{job_id})."""

import uuid

from jobs.infrastructure.models.job_model import JobModel
from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel


def _create_job(test_db, **kwargs) -> JobModel:
    defaults = dict(
        id=str(uuid.uuid7()),
        url="https://example.com/job",
        title="Software Engineer",
        role="SWE",
        company="Tech Corp",
        location="Berlin",
        work_types=["Remote"],
        employment_types=["Full-time"],
        status="imported",
        deleted=0,
        workflow_log="[]",
        rescoring=0,
        user_id="test-user",
    )
    defaults.update(kwargs)
    defaults.pop("num", None)
    job = JobModel(**defaults)
    test_db.add(job)
    test_db.commit()
    return job


def _create_execution(test_db, job_id: str, execution_id: str = "exec-1"):
    model = ProcessingExecutionModel(
        id=execution_id,
        execution_type="job_processing",
        status="completed",
        target_type="job",
        target_id=job_id,
    )
    test_db.add(model)
    test_db.commit()
    return model


class TestDeleteJobAPI:
    def test_delete_job_and_executions(self, client, test_db):
        job = _create_job(test_db, title="Doomed")
        _create_execution(test_db, job.id, "exec-1")
        _create_execution(test_db, job.id, "exec-2")

        resp = client.delete(f"/api/jobs/{job.id}")

        assert resp.status_code == 204
        assert test_db.query(JobModel).filter(JobModel.id == job.id).first() is None
        assert test_db.query(ProcessingExecutionModel).filter(
            ProcessingExecutionModel.target_id == job.id
        ).count() == 0

    def test_delete_job_cascades_analysis_and_summary(self, client, test_db):
        from jobs.infrastructure.models.job_analysis_model import JobAnalysisModel
        from jobs.infrastructure.models.misc_models import SummaryModel

        job = _create_job(test_db, title="Doomed")
        test_db.add(JobAnalysisModel(job_id=job.id, user_id="test-user", recommendation="apply"))
        test_db.add(SummaryModel(job_id=job.id, user_id="test-user", summary="s"))
        test_db.commit()

        resp = client.delete(f"/api/jobs/{job.id}")

        assert resp.status_code == 204
        assert test_db.query(JobAnalysisModel).filter(
            JobAnalysisModel.job_id == job.id
        ).count() == 0
        assert test_db.query(SummaryModel).filter(
            SummaryModel.job_id == job.id
        ).count() == 0

    def test_delete_non_existent_returns_404(self, client):
        resp = client.delete("/api/jobs/nonexistent-id")
        assert resp.status_code == 404

    def test_delete_keeps_other_jobs(self, client, test_db):
        job = _create_job(test_db, title="Doomed")
        other = _create_job(test_db, title="Keep", url="https://other.example")
        resp = client.delete(f"/api/jobs/{job.id}")
        assert resp.status_code == 204
        assert test_db.query(JobModel).filter(JobModel.id == other.id).first() is not None