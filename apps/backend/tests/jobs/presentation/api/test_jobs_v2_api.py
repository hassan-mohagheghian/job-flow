"""Tests for the new Jobs V2 API (GET /api/jobs/list)."""

import pytest
from datetime import datetime, UTC, timedelta
from jobs.infrastructure.models.job_model import JobModel
from jobs.infrastructure.models.job_analysis_model import JobAnalysisModel
from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel
from companies.infrastructure.models.company_model import CompanyModel
from applications.infrastructure.models.application_model import ApplicationModel


def _create_application(test_db, job_id: str, status: str) -> ApplicationModel:
    import uuid
    model = ApplicationModel(
        id=str(uuid.uuid7()),
        job_id=job_id,
        status=status,
        user_id="test-user",
    )
    test_db.add(model)
    test_db.commit()
    return model


def _create_job(test_db, **kwargs) -> JobModel:
    defaults = dict(
        id=None,
        url="https://example.com/job",
        title="Software Engineer",
        company="Tech Corp",
        location="Berlin",
        work_types='["Remote"]',
        visa="Yes",
        status="imported",
        deleted=0,
        workflow_log="[]",
        locations="[]",
        employment_types='["Full-time"]',
        rescoring=0,
        overall_score=85,
        fit_score=80,
        success_score=90,
        user_id="test-user",
    )
    defaults.update(kwargs)
    if defaults["id"] is None:
        import uuid
        defaults["id"] = str(uuid.uuid7())
    job = JobModel(**defaults)
    test_db.add(job)
    test_db.commit()
    return job


_execution_counter = iter(range(1, 1000))


def _create_execution(test_db, job_id: str, status: str = "completed", execution_id: str | None = None):
    import uuid
    seq = next(_execution_counter)
    created_at = f"2026-08-01T10:00:{seq:03d}.000Z"
    model = ProcessingExecutionModel(
        id=execution_id or str(uuid.uuid7()),
        execution_type="job_processing",
        status=status,
        target_type="job",
        target_id=job_id,
        user_id="test-user",
        created_at=created_at,
        started_at=created_at,
        finished_at=created_at,
    )
    test_db.add(model)
    test_db.commit()
    return model


def _create_analysis(test_db, job_id: str, recommendation: str, user_id: str = "test-user"):
    model = JobAnalysisModel(job_id=job_id, recommendation=recommendation, payload=None, user_id=user_id)
    test_db.add(model)
    test_db.commit()
    return model


class TestJobListV2API:
    def test_list_empty(self, client):
        resp = client.get("/api/jobs/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["pagination"]["total_items"] == 0
        assert data["pagination"]["page"] == 1

    def test_list_with_jobs(self, client, test_db):
        _create_job(test_db, id=1, title="Engineer One", company="Alpha Corp")
        _create_job(test_db, id=2, title="Engineer Two", company="Beta Inc")

        resp = client.get("/api/jobs/list")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["pagination"]["total_items"] == 2

    def test_pagination(self, client, test_db):
        for i in range(5):
            _create_job(test_db, id=i + 1, title=f"Job {i}")

        resp = client.get("/api/jobs/list?page=1&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["pagination"]["total_items"] == 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_pages"] == 3

        resp2 = client.get("/api/jobs/list?page=3&page_size=2")
        data2 = resp2.json()
        assert len(data2["items"]) == 1

    def test_search_by_title(self, client, test_db):
        _create_job(test_db, id=1, title="Senior Backend Engineer")
        _create_job(test_db, id=2, title="Junior Frontend Developer")
        _create_job(test_db, id=3, title="DevOps Engineer")

        resp = client.get("/api/jobs/list?query=Backend")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Senior Backend Engineer"

    def test_search_by_company(self, client, test_db):
        _create_job(test_db, id=1, title="Engineer", company="Google")
        _create_job(test_db, id=2, title="Engineer", company="Meta")

        resp = client.get("/api/jobs/list?query=Google")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["company_name"] == "Google"

    def test_search_by_location(self, client, test_db):
        _create_job(test_db, id=1, title="Engineer", location="Berlin")
        _create_job(test_db, id=2, title="Engineer", location="Munich")

        resp = client.get("/api/jobs/list?query=Berlin")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["location"] == "Berlin"

    def test_sort_by_created_at(self, client, test_db):
        _create_job(test_db, id=1, title="A")
        _create_job(test_db, id=2, title="B")

        resp = client.get("/api/jobs/list?sort=created_at&order=asc")
        data = resp.json()
        assert len(data["items"]) == 2
        assert isinstance(data["items"][0]["id"], str) and len(data["items"][0]["id"]) > 0
        assert data["items"][0]["title"] == "A"

        resp = client.get("/api/jobs/list?sort=created_at&order=desc")
        data = resp.json()
        assert data["items"][0]["title"] == "B"

    def test_sort_by_score(self, client, test_db):
        _create_job(test_db, id=1, title="Low", overall_score=50)
        _create_job(test_db, id=2, title="High", overall_score=99)

        resp = client.get("/api/jobs/list?sort=overall_score&order=desc")
        data = resp.json()
        assert data["items"][0]["scores"]["overall"] == 99

    def test_sort_score_nulls_last(self, client, test_db):
        _create_job(test_db, id=1, title="High", overall_score=99)
        _create_job(test_db, id=2, title="Null", overall_score=None)
        _create_job(test_db, id=3, title="Low", overall_score=40)

        resp = client.get("/api/jobs/list?sort=overall_score&order=desc")
        data = resp.json()
        assert [i["title"] for i in data["items"]] == ["High", "Low", "Null"]

        resp = client.get("/api/jobs/list?sort=overall_score&order=asc")
        data = resp.json()
        assert [i["title"] for i in data["items"]] == ["Low", "High", "Null"]

    def test_sort_score_cursor_reaches_null_tail(self, client, test_db):
        for i in range(4):
            _create_job(test_db, id=i + 1, title=f"Scored-{i}", overall_score=90 - i)
        _create_job(test_db, id=5, title="Unscored-A", overall_score=None)
        _create_job(test_db, id=6, title="Unscored-B", overall_score=None)

        resp = client.get("/api/jobs/list?sort=overall_score&order=desc&page_size=3")
        data = resp.json()
        assert [i["title"] for i in data["items"]] == ["Scored-0", "Scored-1", "Scored-2"]
        next_cursor = data["cursor_pagination"]["next_cursor"]
        assert next_cursor is not None

        resp2 = client.get(
            f"/api/jobs/list?sort=overall_score&order=desc&page_size=3&cursor={next_cursor}"
        )
        data2 = resp2.json()
        assert [i["title"] for i in data2["items"]] == ["Scored-3", "Unscored-B", "Unscored-A"]
        assert data2["cursor_pagination"]["has_more"] is False

    def test_filter_by_processing_status(self, client, test_db):
        queued_job = _create_job(test_db, id=1, title="Queued")
        completed_job = _create_job(test_db, id=2, title="Completed")
        _create_job(test_db, id=3, title="Imported")
        _create_execution(test_db, queued_job.id, status="queued")
        _create_execution(test_db, completed_job.id, status="completed")

        resp = client.get("/api/jobs/list?processing_status=queued")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Queued"

        resp = client.get("/api/jobs/list?processing_status=completed")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Completed"

    def test_filter_uses_latest_execution_only(self, client, test_db):
        job = _create_job(test_db, id=1, title="Reprocessed")
        _create_execution(test_db, job.id, status="failed", execution_id="exec-1")
        _create_execution(test_db, job.id, status="completed", execution_id="exec-2")

        resp = client.get("/api/jobs/list?processing_status=completed")
        data = resp.json()
        assert len(data["items"]) == 1

        resp = client.get("/api/jobs/list?processing_status=failed")
        data = resp.json()
        assert len(data["items"]) == 0

    def test_filter_processing_status_none(self, client, test_db):
        processed = _create_job(test_db, id=1, title="Processed")
        _create_job(test_db, id=2, title="Fresh")
        _create_execution(test_db, processed.id, status="completed")

        resp = client.get("/api/jobs/list?processing_status=none")
        data = resp.json()

        assert data["pagination"]["total_items"] == 1
        assert [i["title"] for i in data["items"]] == ["Fresh"]
        assert data["items"][0]["latest_processing_execution"] is None

    def test_filter_processing_status_none_empty(self, client, test_db):
        job = _create_job(test_db, id=1, title="Processed")
        _create_execution(test_db, job.id, status="completed")

        resp = client.get("/api/jobs/list?processing_status=none")
        data = resp.json()

        assert data["pagination"]["total_items"] == 0
        assert data["items"] == []

    def test_sort_status_uses_latest_execution_unprocessed_last(self, client, test_db):
        job_a = _create_job(test_db, id=1, title="Done")
        _create_job(test_db, id=2, title="Fresh")
        job_c = _create_job(test_db, id=3, title="Queued")
        _create_execution(test_db, job_a.id, status="completed", execution_id="a-1")
        _create_execution(test_db, job_c.id, status="queued", execution_id="c-1")

        resp = client.get("/api/jobs/list?sort=status&order=asc")
        data = resp.json()

        assert [i["title"] for i in data["items"]] == ["Done", "Queued", "Fresh"]

        resp = client.get("/api/jobs/list?sort=status&order=desc")
        data = resp.json()

        assert [i["title"] for i in data["items"]] == ["Queued", "Done", "Fresh"]

    def test_sort_status_cursor_paginates(self, client, test_db):
        job_a = _create_job(test_db, id=1, title="Done")
        _create_job(test_db, id=2, title="Fresh")
        _create_execution(test_db, job_a.id, status="completed", execution_id="a-1")

        resp = client.get("/api/jobs/list?sort=status&order=desc&page_size=1")
        data = resp.json()
        assert len(data["items"]) == 1
        next_cursor = data["cursor_pagination"]["next_cursor"]
        assert next_cursor is not None

        resp2 = client.get(
            f"/api/jobs/list?sort=status&order=desc&page_size=1&cursor={next_cursor}"
        )
        data2 = resp2.json()
        assert data2["cursor_pagination"]["has_more"] is False
        assert data2["items"][0]["title"] == "Fresh"

    def test_filter_by_remote(self, client, test_db):
        _create_job(test_db, id=1, title="Remote", work_types='["Remote"]')
        _create_job(test_db, id=2, title="Onsite", work_types='["On-site"]')

        resp = client.get("/api/jobs/list?remote=true")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["remote"] is True

        resp = client.get("/api/jobs/list?remote=false")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["remote"] is False

    def test_filter_by_visa(self, client, test_db):
        _create_job(test_db, id=1, title="Has Visa", visa="Yes")
        _create_job(test_db, id=2, title="No Visa", visa="")

        resp = client.get("/api/jobs/list?visa=true")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["visa_sponsorship"] is True

    def test_filter_by_location(self, client, test_db):
        _create_job(test_db, id=1, title="Berlin Job", location="Berlin, Germany")
        _create_job(test_db, id=2, title="Amsterdam Job", location="Amsterdam, Netherlands")

        resp = client.get("/api/jobs/list?location=germany")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["location"] == "Berlin, Germany"

        resp = client.get("/api/jobs/list?location=Berlin")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Berlin Job"

        resp = client.get("/api/jobs/list?location=Madrid")
        data = resp.json()
        assert data["pagination"]["total_items"] == 0

    def test_filter_by_score_range(self, client, test_db):
        _create_job(test_db, id=1, title="Low", overall_score=30)
        _create_job(test_db, id=2, title="Mid", overall_score=60)
        _create_job(test_db, id=3, title="High", overall_score=95)

        resp = client.get("/api/jobs/list?overall_score_min=50&overall_score_max=100")
        data = resp.json()
        assert len(data["items"]) == 2

    def test_response_shape(self, client, test_db):
        job = _create_job(
            test_db, id=1, title="Engineer", company="Corp", location="Berlin",
            work_types='["Remote"]', visa="Yes", overall_score=85, fit_score=80,
            success_score=90,
        )
        _create_execution(test_db, job.id, status="completed", execution_id="exec-1")

        resp = client.get("/api/jobs/list")
        data = resp.json()
        item = data["items"][0]

        assert isinstance(item["id"], str) and len(item["id"]) > 0
        assert item["title"] == "Engineer"
        assert item["company_name"] == "Corp"
        assert item["location"] == "Berlin"
        assert item["remote"] is True
        assert item["visa_sponsorship"] is True
        assert item["job_status"] == "completed"
        assert item["scores"]["overall"] == 85
        assert item["scores"]["fit"] == 80
        assert item["scores"]["success"] == 90
        assert item["latest_processing_execution"] is not None
        assert item["latest_processing_execution"]["id"] == "exec-1"
        assert item["latest_processing_execution"]["status"] == "completed"
        assert item["latest_processing_execution"]["started_at"] is not None
        assert item["latest_processing_execution"]["finished_at"] is not None
        assert "updated_at" in item
        assert "created_at" in item

    def test_response_without_execution_has_null_status(self, client, test_db):
        _create_job(test_db, id=1, title="Imported", status="imported")

        resp = client.get("/api/jobs/list")
        data = resp.json()
        item = data["items"][0]

        assert item["title"] == "Imported"
        assert item["job_status"] is None
        assert item["latest_processing_execution"] is None

    def test_list_returns_latest_execution(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer")
        _create_execution(test_db, job.id, status="failed", execution_id="exec-old")
        _create_execution(test_db, job.id, status="completed", execution_id="exec-new")

        resp = client.get("/api/jobs/list")
        data = resp.json()
        execution = data["items"][0]["latest_processing_execution"]

        assert execution["id"] == "exec-new"
        assert execution["status"] == "completed"

    def test_completed_job_is_listed_with_persisted_fields(self, client, test_db):
        """Processed job keeps its persisted title + completed status across reloads.

        A job analysed by the pipeline (title written to the jobs row, execution
        finished) must surface that state in the list — not the legacy jobs.status.
        """
        job = _create_job(test_db, id=1, title="")
        _create_execution(test_db, job.id, status="completed", execution_id="exec-1")

        resp = client.get("/api/jobs/list?processing_status=completed")
        data = resp.json()

        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["job_status"] == "completed"
        assert item["latest_processing_execution"]["id"] == "exec-1"
        assert item["latest_processing_execution"]["status"] == "completed"

        resp2 = client.get("/api/jobs/list")
        data2 = resp2.json()
        assert len(data2["items"]) == 1
        assert data2["items"][0]["job_status"] == "completed"

    def test_invalid_page_returns_422(self, client):
        resp = client.get("/api/jobs/list?page=0")
        assert resp.status_code == 422

    def test_invalid_page_size_returns_422(self, client):
        resp = client.get("/api/jobs/list?page_size=0")
        assert resp.status_code == 422

    def test_page_size_greater_than_max_returns_422(self, client):
        resp = client.get("/api/jobs/list?page_size=200")
        assert resp.status_code == 422

    def test_sort_fallback(self, client, test_db):
        _create_job(test_db, id=1, title="A")
        _create_job(test_db, id=2, title="B")

        resp = client.get("/api/jobs/list?sort=invalid_field")
        assert resp.status_code == 200
        # Should fall back to updated_at desc and not error

    def test_not_found_filters_return_empty(self, client, test_db):
        _create_job(test_db, id=1, title="Engineer")

        resp = client.get("/api/jobs/list?company_id=999")
        data = resp.json()
        assert len(data["items"]) == 0


class TestJobPinnedV2API:
    def test_list_item_carries_pinned_default_false(self, client, test_db):
        _create_job(test_db, id=1, title="Engineer")

        resp = client.get("/api/jobs/list")
        data = resp.json()
        assert data["items"][0]["pinned"] is False

    def test_filter_by_pinned(self, client, test_db):
        _create_job(test_db, id=1, title="Pinned", pinned=1)
        _create_job(test_db, id=2, title="Plain")

        resp = client.get("/api/jobs/list?pinned=true")
        data = resp.json()
        assert [i["title"] for i in data["items"]] == ["Pinned"]

        resp = client.get("/api/jobs/list?pinned=false")
        data = resp.json()
        assert [i["title"] for i in data["items"]] == ["Plain"]

        resp = client.get("/api/jobs/list")
        data = resp.json()
        assert len(data["items"]) == 2

    def test_set_pinned_persists_and_toggles(self, client, test_db):
        job = _create_job(test_db, id=1, title="Pinned")

        resp = client.put(f"/api/jobs/{job.id}/pinned", json={"pinned": True})
        assert resp.status_code == 200
        assert resp.json() == {"pinned": True}

        data = client.get("/api/jobs/list").json()
        assert data["items"][0]["pinned"] is True
        assert [i["title"] for i in client.get("/api/jobs/list?pinned=true").json()["items"]] == ["Pinned"]

        resp = client.put(f"/api/jobs/{job.id}/pinned", json={"pinned": False})
        assert resp.status_code == 200
        data = client.get("/api/jobs/list").json()
        assert data["items"][0]["pinned"] is False

    def test_get_detail_carries_pinned(self, client, test_db):
        job = _create_job(test_db, id=1, title="Pinned")

        assert client.get(f"/api/jobs/{job.id}").json()["pinned"] is False

        client.put(f"/api/jobs/{job.id}/pinned", json={"pinned": True})
        assert client.get(f"/api/jobs/{job.id}").json()["pinned"] is True

    def test_set_pinned_missing_job_returns_404(self, client, test_db):
        resp = client.put("/api/jobs/does-not-exist/pinned", json={"pinned": True})
        assert resp.status_code == 404


class TestJobDismissedV2API:
    def test_list_item_carries_dismissed_default_false(self, client, test_db):
        _create_job(test_db, id=1, title="Engineer")

        data = client.get("/api/jobs/list").json()
        assert data["items"][0]["dismissed"] is False

    def test_default_list_includes_dismissed(self, client, test_db):
        _create_job(test_db, id=1, title="Visible")
        _create_job(test_db, id=2, title="Dismissed", dismissed=1)

        data = client.get("/api/jobs/list").json()
        titles = [i["title"] for i in data["items"]]
        assert "Visible" in titles
        assert "Dismissed" in titles

    def test_filter_show_only_dismissed(self, client, test_db):
        _create_job(test_db, id=1, title="Visible")
        _create_job(test_db, id=2, title="Dismissed", dismissed=1)

        data = client.get("/api/jobs/list?dismissed=true").json()
        assert [i["title"] for i in data["items"]] == ["Dismissed"]
        assert all(i["dismissed"] for i in data["items"])

    def test_set_dismissed_persists_and_toggles(self, client, test_db):
        job = _create_job(test_db, id=1, title="Recommended")

        resp = client.put(f"/api/jobs/{job.id}/dismissed", json={"dismissed": True})
        assert resp.status_code == 200
        assert resp.json() == {"dismissed": True}

        # Visible in the default list with dismissed flag.
        data = client.get("/api/jobs/list").json()
        assert len(data["items"]) == 1
        assert data["items"][0]["dismissed"] is True

        resp = client.put(f"/api/jobs/{job.id}/dismissed", json={"dismissed": False})
        assert resp.status_code == 200
        data = client.get("/api/jobs/list").json()
        assert [i["title"] for i in data["items"]] == ["Recommended"]
        assert data["items"][0]["dismissed"] is False

    def test_set_dismissed_with_note_appends_to_job_notes(self, client, test_db):
        job = _create_job(test_db, id=1, title="To Dismiss")

        resp = client.put(f"/api/jobs/{job.id}/dismissed", json={"dismissed": True, "note": "Not relevant to my search"})
        assert resp.status_code == 200

        detail = client.get(f"/api/jobs/{job.id}").json()
        assert len(detail["notes"]) == 1
        assert detail["notes"][0]["content"] == "Not relevant to my search"

    def test_set_dismissed_without_note_does_not_add_note(self, client, test_db):
        job = _create_job(test_db, id=1, title="To Dismiss")

        resp = client.put(f"/api/jobs/{job.id}/dismissed", json={"dismissed": True})
        assert resp.status_code == 200

        detail = client.get(f"/api/jobs/{job.id}").json()
        assert detail["notes"] == []

    def test_set_dismissed_missing_job_returns_404(self, client, test_db):
        resp = client.put("/api/jobs/does-not-exist/dismissed", json={"dismissed": True})
        assert resp.status_code == 404


class TestJobTagsV2API:
    def test_list_item_carries_empty_tags(self, client, test_db):
        _create_job(test_db, id=1, title="Engineer")
        data = client.get("/api/jobs/list").json()
        assert data["items"][0]["tags"] == []

    def test_set_tags_persists(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer")
        resp = client.put(f"/api/jobs/{job.id}/tags", json={"tags": ["python", "remote"]})
        assert resp.status_code == 200
        assert resp.json() == {"tags": ["python", "remote"]}

        data = client.get("/api/jobs/list").json()
        assert data["items"][0]["tags"] == ["python", "remote"]

    def test_set_tags_replaces_existing(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer")
        client.put(f"/api/jobs/{job.id}/tags", json={"tags": ["python", "remote"]})
        client.put(f"/api/jobs/{job.id}/tags", json={"tags": ["java"]})

        data = client.get("/api/jobs/list").json()
        assert data["items"][0]["tags"] == ["java"]

    def test_filter_by_single_tag(self, client, test_db):
        j1 = _create_job(test_db, id=1, title="Python Dev")
        j2 = _create_job(test_db, id=2, title="Java Dev")
        client.put(f"/api/jobs/{j1.id}/tags", json={"tags": ["python"]})
        client.put(f"/api/jobs/{j2.id}/tags", json={"tags": ["java"]})

        data = client.get("/api/jobs/list?tags=python").json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "Python Dev"

    def test_filter_by_multiple_tags_intersects(self, client, test_db):
        j1 = _create_job(test_db, id=1, title="A")
        j2 = _create_job(test_db, id=2, title="B")
        j3 = _create_job(test_db, id=3, title="C")
        client.put(f"/api/jobs/{j1.id}/tags", json={"tags": ["python", "remote"]})
        client.put(f"/api/jobs/{j2.id}/tags", json={"tags": ["python"]})
        client.put(f"/api/jobs/{j3.id}/tags", json={"tags": ["remote"]})

        data = client.get("/api/jobs/list?tags=python,remote").json()
        titles = [i["title"] for i in data["items"]]
        assert "A" in titles
        assert "B" not in titles
        assert "C" not in titles

    def test_set_tags_missing_job_returns_404(self, client, test_db):
        resp = client.put("/api/jobs/does-not-exist/tags", json={"tags": ["x"]})
        assert resp.status_code == 404


class TestJobRecommendationV2API:
    def test_list_item_carries_recommendation_field(self, client, test_db):
        _create_job(test_db, id=1, title="Engineer")

        resp = client.get("/api/jobs/list")
        data = resp.json()
        assert data["items"][0]["recommendation"] is None

    def test_recommendation_populated_from_analysis(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer")
        _create_analysis(test_db, job.id, recommendation="apply")

        resp = client.get("/api/jobs/list")
        data = resp.json()
        assert data["items"][0]["recommendation"] == "apply"

    def test_recommendation_null_without_analysis(self, client, test_db):
        _create_job(test_db, id=1, title="Engineer", overall_score=90)

        resp = client.get("/api/jobs/list")
        data = resp.json()
        assert data["items"][0]["recommendation"] is None


class TestJobRecommendationFilterV2API:
    def test_filter_by_recommendation(self, client, test_db):
        apply_job = _create_job(test_db, id=1, title="Apply Job")
        consider_job = _create_job(test_db, id=2, title="Consider Job")
        skip_job = _create_job(test_db, id=3, title="Skip Job")
        _create_analysis(test_db, apply_job.id, recommendation="apply")
        _create_analysis(test_db, consider_job.id, recommendation="consider")
        _create_analysis(test_db, skip_job.id, recommendation="skip")

        resp = client.get("/api/jobs/list?recommendation=apply")
        assert resp.status_code == 200
        assert [i["title"] for i in resp.json()["items"]] == ["Apply Job"]

        resp = client.get("/api/jobs/list?recommendation=consider")
        assert [i["title"] for i in resp.json()["items"]] == ["Consider Job"]

        resp = client.get("/api/jobs/list?recommendation=skip")
        assert [i["title"] for i in resp.json()["items"]] == ["Skip Job"]

    def test_recommendation_filter_excludes_jobs_without_analysis(self, client, test_db):
        apply_job = _create_job(test_db, id=1, title="Apply Job")
        _create_job(test_db, id=2, title="No Analysis", overall_score=95)
        _create_analysis(test_db, apply_job.id, recommendation="apply")

        resp = client.get("/api/jobs/list?recommendation=apply")
        data = resp.json()
        assert [i["title"] for i in data["items"]] == ["Apply Job"]

    def test_recommendation_filter_combines_with_pinned(self, client, test_db):
        apply_job = _create_job(test_db, id=1, title="Pinned Apply", pinned=1)
        plain_job = _create_job(test_db, id=2, title="Plain Apply")
        _create_analysis(test_db, apply_job.id, recommendation="apply")
        _create_analysis(test_db, plain_job.id, recommendation="apply")

        resp = client.get("/api/jobs/list?recommendation=apply&pinned=true")
        data = resp.json()
        assert [i["title"] for i in data["items"]] == ["Pinned Apply"]

    def test_invalid_recommendation_returns_422(self, client, test_db):
        resp = client.get("/api/jobs/list?recommendation=bogus")
        assert resp.status_code == 422

    def test_filter_by_recommendation_multi(self, client, test_db):
        apply_job = _create_job(test_db, id=1, title="Apply Job")
        consider_job = _create_job(test_db, id=2, title="Consider Job")
        skip_job = _create_job(test_db, id=3, title="Skip Job")
        _create_analysis(test_db, apply_job.id, recommendation="apply")
        _create_analysis(test_db, consider_job.id, recommendation="consider")
        _create_analysis(test_db, skip_job.id, recommendation="skip")

        resp = client.get("/api/jobs/list?recommendation=apply&recommendation=consider")
        assert resp.status_code == 200
        assert {i["title"] for i in resp.json()["items"]} == {"Apply Job", "Consider Job"}


class TestJobCreatedDateFilterV2API:
    @staticmethod
    def _iso(dt: datetime) -> str:
        return dt.replace(tzinfo=None).isoformat()

    def test_filter_by_today(self, client, test_db):
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        _create_job(test_db, id=1, title="Today Job", created_at=self._iso(today_start + timedelta(hours=10)))
        _create_job(test_db, id=2, title="Old Job", created_at=self._iso(today_start - timedelta(days=10)))

        resp = client.get("/api/jobs/list?created_date=today")
        assert resp.status_code == 200
        assert [i["title"] for i in resp.json()["items"]] == ["Today Job"]

    def test_filter_by_week(self, client, test_db):
        now = datetime.now(UTC)
        _create_job(test_db, id=1, title="Week Job", created_at=self._iso(now - timedelta(days=5)))
        _create_job(test_db, id=2, title="Old Job", created_at=self._iso(now - timedelta(days=10)))

        resp = client.get("/api/jobs/list?created_date=week")
        assert [i["title"] for i in resp.json()["items"]] == ["Week Job"]

    def test_invalid_created_date_returns_422(self, client, test_db):
        resp = client.get("/api/jobs/list?created_date=fortnight")
        assert resp.status_code == 422


class TestJobTrackingFilterV2API:
    def test_list_item_carries_tracking_status(self, client, test_db):
        job = _create_job(test_db, id=1, title="Applied Job")
        _create_job(test_db, id=2, title="Not Applied Job")
        _create_application(test_db, job.id, "applied")

        resp = client.get("/api/jobs/list")
        assert resp.status_code == 200
        by_title = {i["title"]: i for i in resp.json()["items"]}
        assert by_title["Applied Job"]["tracking_status"] == "applied"
        assert by_title["Not Applied Job"]["tracking_status"] == "not_applied"

    def test_filter_by_tracking_status(self, client, test_db):
        applied = _create_job(test_db, id=1, title="Applied")
        interview = _create_job(test_db, id=2, title="Interview")
        not_applied = _create_job(test_db, id=3, title="Not Applied")
        _create_application(test_db, applied.id, "applied")
        _create_application(test_db, interview.id, "interview")

        resp = client.get("/api/jobs/list?tracking_status=applied")
        assert [i["title"] for i in resp.json()["items"]] == ["Applied"]

        resp = client.get("/api/jobs/list?tracking_status=interview")
        assert [i["title"] for i in resp.json()["items"]] == ["Interview"]

        resp = client.get("/api/jobs/list?tracking_status=not_applied")
        assert [i["title"] for i in resp.json()["items"]] == ["Not Applied"]

    def test_tracking_filter_combines_with_processing_status(self, client, test_db):
        applied = _create_job(test_db, id=1, title="Applied Processed")
        other_applied = _create_job(test_db, id=2, title="Applied Other")
        _create_application(test_db, applied.id, "applied")
        _create_application(test_db, other_applied.id, "applied")
        _create_execution(test_db, applied.id, status="completed")

        resp = client.get("/api/jobs/list?tracking_status=applied&processing_status=completed")
        assert [i["title"] for i in resp.json()["items"]] == ["Applied Processed"]

    def test_filter_by_tracking_status_multi(self, client, test_db):
        applied = _create_job(test_db, id=1, title="Applied")
        interview = _create_job(test_db, id=2, title="Interview")
        _create_job(test_db, id=3, title="Not Applied")
        _create_application(test_db, applied.id, "applied")
        _create_application(test_db, interview.id, "interview")

        resp = client.get("/api/jobs/list?tracking_status=applied&tracking_status=interview")
        assert resp.status_code == 200
        assert {i["title"] for i in resp.json()["items"]} == {"Applied", "Interview"}

    def test_filter_by_tracking_status_comma_form(self, client, test_db):
        applied = _create_job(test_db, id=1, title="Applied")
        interview = _create_job(test_db, id=2, title="Interview")
        _create_application(test_db, applied.id, "applied")
        _create_application(test_db, interview.id, "interview")

        resp = client.get("/api/jobs/list?tracking_status=applied,interview")
        assert resp.status_code == 200
        assert {i["title"] for i in resp.json()["items"]} == {"Applied", "Interview"}

    def test_invalid_tracking_status_returns_422(self, client, test_db):
        resp = client.get("/api/jobs/list?tracking_status=bogus")
        assert resp.status_code == 422


def _create_company(test_db, **kwargs) -> CompanyModel:
    import uuid

    defaults = dict(name="Acme GmbH", user_id="test-user")
    defaults.update(kwargs)
    defaults.setdefault("id", str(uuid.uuid7()))
    company = CompanyModel(**defaults)
    test_db.add(company)
    test_db.commit()
    return company


class TestJobRankV2API:
    def test_job_detail_returns_overall_score_rank(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer", overall_score=85)
        _create_job(test_db, id=2, title="Better", overall_score=92)

        resp = client.get(f"/api/jobs/{job.id}")
        assert resp.status_code == 200
        assert resp.json()["rank"] == 2

    def test_job_detail_top_rank_is_one(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer", overall_score=92)
        _create_job(test_db, id=2, title="Other", overall_score=40)

        resp = client.get(f"/api/jobs/{job.id}")
        assert resp.status_code == 200
        assert resp.json()["rank"] == 1

    def test_job_detail_success_breaks_overall_tie(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer", overall_score=85, success_score=60)
        _create_job(test_db, id=2, title="Other", overall_score=85, success_score=95)

        # Same overall, but job-2 has higher success -> ranks above job-1.
        resp = client.get(f"/api/jobs/{job.id}")
        assert resp.status_code == 200
        assert resp.json()["rank"] == 2

    def test_job_detail_fit_breaks_overall_and_success_tie(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer", overall_score=85, success_score=70, fit_score=40)
        _create_job(test_db, id=2, title="Other", overall_score=85, success_score=70, fit_score=95)

        resp = client.get(f"/api/jobs/{job.id}")
        assert resp.status_code == 200
        assert resp.json()["rank"] == 2

    def test_job_detail_equal_scores_share_rank(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer", overall_score=85, success_score=70, fit_score=60)
        _create_job(test_db, id=2, title="Twin", overall_score=85, success_score=70, fit_score=60)
        _create_job(test_db, id=3, title="Lower", overall_score=30)

        resp = client.get(f"/api/jobs/{job.id}")
        assert resp.status_code == 200
        # Competition ranking: job-1 and job-2 tie for rank 1.
        assert resp.json()["rank"] == 1


class TestJobListRankV2API:
    def test_list_items_carry_rank(self, client, test_db):
        _create_job(test_db, id=1, title="Low", overall_score=50)
        job = _create_job(test_db, id=2, title="Top", overall_score=90)
        _create_job(test_db, id=3, title="Mid", overall_score=70)

        resp = client.get("/api/jobs/list")
        assert resp.status_code == 200
        by_title = {i["title"]: i.get("rank") for i in resp.json()["items"]}
        assert by_title["Top"] == 1
        assert by_title["Mid"] == 2
        assert by_title["Low"] == 3

    def test_equal_scores_share_rank(self, client, test_db):
        _create_job(test_db, id=1, title="A", overall_score=90, success_score=80, fit_score=70)
        _create_job(test_db, id=2, title="B", overall_score=90, success_score=80, fit_score=70)
        _create_job(test_db, id=3, title="C", overall_score=40)

        resp = client.get("/api/jobs/list")
        assert resp.status_code == 200
        by_title = {i["title"]: i.get("rank") for i in resp.json()["items"]}
        assert by_title["A"] == 1
        assert by_title["B"] == 1
        assert by_title["C"] == 3

    def test_rank_is_absolute_over_full_set(self, client, test_db):
        # The page is sorted by default (created/updated), so the visible order
        # is not by score; ranks are still absolute positions in the score order.
        _create_job(test_db, id=1, title="Low", overall_score=30)
        _create_job(test_db, id=2, title="Top", overall_score=95)
        _create_job(test_db, id=3, title="Mid", overall_score=60)

        resp = client.get("/api/jobs/list?sort=created_at&order=desc")
        assert resp.status_code == 200
        by_title = {i["title"]: i.get("rank") for i in resp.json()["items"]}
        assert by_title["Low"] == 3
        assert by_title["Top"] == 1
        assert by_title["Mid"] == 2


class TestJobCompanyV2API:
    def test_set_company_links_job_and_sets_canonical_name(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer", company="Old Name")
        company = _create_company(test_db, company_type="PRODUCT_COMPANY")

        resp = client.put(f"/api/jobs/{job.id}/company", json={"company_id": company.id})
        assert resp.status_code == 200
        body = resp.json()
        assert body["company_id"] == company.id
        assert body["company_name"] == "Acme GmbH"
        assert body["company_type"] == "PRODUCT_COMPANY"

    def test_job_detail_includes_company_type(self, client, test_db):
        company = _create_company(test_db, company_type="CONSULTING_COMPANY")
        job = _create_job(test_db, id=1, title="Engineer", company="Acme GmbH", company_id=company.id)

        resp = client.get(f"/api/jobs/{job.id}")
        assert resp.status_code == 200
        assert resp.json()["company_type"] == "CONSULTING_COMPANY"

    def test_job_detail_company_type_is_none_when_unlinked(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer", company="Acme GmbH")

        resp = client.get(f"/api/jobs/{job.id}")
        assert resp.status_code == 200
        assert resp.json()["company_type"] is None

    def test_set_company_null_unlinks_without_touching_name(self, client, test_db):
        company = _create_company(test_db)
        job = _create_job(test_db, id=1, title="Engineer", company="Acme GmbH", company_id=company.id)

        resp = client.put(f"/api/jobs/{job.id}/company", json={"company_id": None})
        assert resp.status_code == 200
        body = resp.json()
        assert body["company_id"] is None
        assert body["company_name"] == "Acme GmbH"

    def test_set_company_empty_string_unlinks(self, client, test_db):
        company = _create_company(test_db)
        job = _create_job(test_db, id=1, title="Engineer", company_id=company.id)

        resp = client.put(f"/api/jobs/{job.id}/company", json={"company_id": ""})
        assert resp.status_code == 200
        assert resp.json()["company_id"] is None

    def test_set_company_missing_job_returns_404(self, client, test_db):
        company = _create_company(test_db)
        resp = client.put("/api/jobs/does-not-exist/company", json={"company_id": company.id})
        assert resp.status_code == 404

    def test_set_company_missing_company_returns_404(self, client, test_db):
        job = _create_job(test_db, id=1, title="Engineer")
        resp = client.put(f"/api/jobs/{job.id}/company", json={"company_id": "does-not-exist"})
        assert resp.status_code == 404


class TestJobTimeline:
    def test_returns_per_day_counts_newest_first(self, client, test_db):
        _create_job(test_db, url="https://a.com/1", created_at="2026-08-19T09:00:00.000Z")
        _create_job(test_db, url="https://a.com/2", created_at="2026-08-19T10:00:00.000Z")
        _create_job(test_db, url="https://a.com/3", created_at="2026-08-18T11:00:00.000Z")

        resp = client.get("/api/jobs/timeline")
        assert resp.status_code == 200
        body = resp.json()
        assert body["days"] == [
            {"date": "2026-08-19", "count": 2},
            {"date": "2026-08-18", "count": 1},
        ]
        assert body["total"] == 3

    def test_excludes_deleted_jobs(self, client, test_db):
        _create_job(test_db, url="https://a.com/1", created_at="2026-08-19T09:00:00.000Z")
        _create_job(test_db, url="https://a.com/2", created_at="2026-08-19T10:00:00.000Z", deleted=1)

        resp = client.get("/api/jobs/timeline").json()
        assert resp["total"] == 1
        assert resp["days"] == [{"date": "2026-08-19", "count": 1}]

    def test_empty_timeline(self, client):
        resp = client.get("/api/jobs/timeline")
        assert resp.status_code == 200
        assert resp.json()["days"] == []
        assert resp.json()["total"] == 0
