"""Extra tests for SQLAlchemyJobRepository (jobs.infrastructure.repositories).

Covers branches not exercised by the legacy suite:
list_jobs filter variants (location/work_types JSONB, filter_status),
sort directions and fields, create_job, get_by_id, set_deleted_by_url
without exclude, lifecycle counts, pick_queued_item, search_jobs and
search_jobs_cursor.
"""

import uuid

import pytest

from datetime import datetime, UTC, timedelta

from jobs.infrastructure.models.job_model import JobModel
from companies.infrastructure.models.company_model import CompanyModel
from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel
from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository


@pytest.fixture
def repo(sa_session):
    return SQLAlchemyJobRepository(sa_session, user_id="test-user")


def _add(session, id=None, url=None, **kwargs):
    defaults = {
        "id": id or str(uuid.uuid7()),
        "url": url or "https://example.com/job",
        "deleted": 0,
        "user_id": "test-user",
    }
    defaults.update(kwargs)
    m = JobModel(**defaults)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def _add_execution(session, job_id: str, status: str, created_at: str):
    model = ProcessingExecutionModel(
        id=str(uuid.uuid7()),
        execution_type="job_processing",
        status=status,
        target_type="job",
        target_id=job_id,
        created_at=created_at,
        started_at=created_at,
        finished_at=None,
    )
    session.add(model)
    session.commit()
    return model


# ── get_by_id ────────────────────────────────────────────────────

class TestGetById:
    def test_company_id_set_but_no_company(self, sa_session, repo):
        m = _add(sa_session, id="job-1", company="Ghost", company_id="00000000-0000-0000-0000-000000000099")
        result = repo.get_by_id(m.id)
        assert result is not None
        assert "linked_company" not in result

    def test_with_linked_company(self, sa_session, repo):
        co = CompanyModel(name="Google", industry="Tech", city="Berlin",
                          country="DE", logo_url="http://x/logo.png", user_id="test-user")
        sa_session.add(co)
        sa_session.commit()
        sa_session.refresh(co)
        m = _add(sa_session, id="job-2", company="Google", company_id=co.id)
        result = repo.get_by_id(m.id)
        assert result["company_id"] == co.id


# ── get_by_ids ───────────────────────────────────────────────────

class TestGetByIds:
    def test_batch_fetches_title_and_location(self, sa_session, repo):
        a = _add(sa_session, id="job-a", title="Engineer", location="Berlin")
        b = _add(sa_session, id="job-b", title="Designer", location="Munich")
        _add(sa_session, id="job-c", deleted=1, title="Deleted", location="Hamburg")

        result = repo.get_by_ids([a.id, b.id, "job-c", "does-not-exist"])
        assert result == [
            {"id": a.id, "title": "Engineer", "location": "Berlin"},
            {"id": b.id, "title": "Designer", "location": "Munich"},
        ]

    def test_empty_input_returns_empty_list(self, sa_session, repo):
        assert repo.get_by_ids([]) == []


class TestGetJobsByIds:
    def test_batch_fetches_full_details(self, sa_session, repo):
        a = _add(sa_session, id="job-a", title="Engineer", role="Engineer",
                 location="Berlin", fit_score=84, success_score=63, overall_score=76)
        b = _add(sa_session, id="job-b", title="Designer", role="Designer",
                 location="Munich", fit_score=90, success_score=70, overall_score=82)
        _add(sa_session, id="job-c", deleted=1, title="Deleted", role="Deleted", location="Hamburg")

        result = repo.get_jobs_by_ids([a.id, b.id, "job-c", "does-not-exist"])
        by_id = {r["id"]: r for r in result}
        assert set(by_id) == {a.id, b.id}
        assert by_id[a.id]["role"] == "Engineer"
        assert by_id[a.id]["location"] == "Berlin"
        assert by_id[a.id]["fit_score"] == 84
        assert by_id[a.id]["success_score"] == 63
        assert by_id[a.id]["overall_score"] == 76
        assert by_id[b.id]["role"] == "Designer"

    def test_empty_input_returns_empty_list(self, sa_session, repo):
        assert repo.get_jobs_by_ids([]) == []


# ── list_jobs ────────────────────────────────────────────────────

class TestListJobs:
    def test_filter_cities_uses_location(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", location="Berlin")
        _add(sa_session, id="job-b", location="Paris")
        jobs, total = repo.list_jobs(filters={"filter_cities": "Berlin"})
        assert total == 1
        assert jobs[0]["id"] == m1.id

    def test_filter_cities_empty_string_ignored(self, sa_session, repo):
        _add(sa_session, id="job-a", location="Berlin")
        jobs, total = repo.list_jobs(filters={"filter_cities": "  "})
        assert total == 1

    def test_filter_work_types_jsonb(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", work_types=["Hybrid"])
        _add(sa_session, id="job-b", work_types=[])
        jobs, total = repo.list_jobs(filters={"filter_work_types": "Hybrid"})
        assert total == 1
        assert jobs[0]["id"] == m1.id

    def test_filter_work_types_is_exact_token(self, sa_session, repo):
        _add(sa_session, id="job-a", work_types=["Remote Work"])
        _add(sa_session, id="job-b", work_types=["Remote"])
        jobs, total = repo.list_jobs(filters={"filter_work_types": "Remote"})
        assert total == 1
        assert jobs[0]["id"] == "job-b"

    def test_filter_status(self, sa_session, repo):
        _add(sa_session, id="job-a", status="imported")
        m2 = _add(sa_session, id="job-b", status="processing")
        jobs, total = repo.list_jobs(filters={"filter_status": "processing"})
        assert total == 1
        assert jobs[0]["id"] == m2.id

    def test_filter_applied_false_is_noop(self, sa_session, repo):
        _add(sa_session, id="job-a")
        jobs, total = repo.list_jobs(filters={"filter_applied": "false"})
        assert total == 1

    def test_sort_created_at_asc(self, sa_session, repo):
        m2 = _add(sa_session, id="job-2", created_at="2026-07-27T10:00:02")
        m1 = _add(sa_session, id="job-1", created_at="2026-07-27T10:00:01")
        jobs, total = repo.list_jobs(sort_by="created_at", sort_dir="asc")
        assert [j["id"] for j in jobs] == [m1.id, m2.id]

    def test_sort_company_desc(self, sa_session, repo):
        _add(sa_session, id="job-a", company="Alpha")
        _add(sa_session, id="job-b", company="Beta")
        jobs, total = repo.list_jobs(sort_by="company", sort_dir="desc")
        assert jobs[0]["company"] == "Beta"

    def test_sort_location_asc(self, sa_session, repo):
        _add(sa_session, id="job-a", location="Berlin")
        _add(sa_session, id="job-b", location="Amsterdam")
        jobs, total = repo.list_jobs(sort_by="location", sort_dir="asc")
        assert jobs[0]["location"] == "Amsterdam"

    def test_sort_applicants(self, sa_session, repo):
        _add(sa_session, id="job-a", applicants="200")
        _add(sa_session, id="job-b", applicants="100")
        jobs, total = repo.list_jobs(sort_by="applicants", sort_dir="desc")
        assert jobs[0]["applicants"] == "200"

    def test_sort_score_desc_nulls_last(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-null")
        _add(sa_session, id="job-b", overall_score=40)
        jobs, total = repo.list_jobs(sort_by="overall_score", sort_dir="desc")
        assert [j["overall_score"] for j in jobs] == [90, 40, None]

    def test_sort_score_asc_nulls_last(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-null")
        _add(sa_session, id="job-b", overall_score=40)
        jobs, total = repo.list_jobs(sort_by="overall_score", sort_dir="asc")
        assert [j["overall_score"] for j in jobs] == [40, 90, None]

    def test_sort_company_desc_nulls_last(self, sa_session, repo):
        _add(sa_session, id="job-a", company="Alpha")
        _add(sa_session, id="job-null")
        jobs, total = repo.list_jobs(sort_by="company", sort_dir="desc")
        assert jobs[0]["company"] == "Alpha"
        assert jobs[-1]["company"] is None

    def test_sort_fallback_invalid_column_and_dir(self, sa_session, repo):
        _add(sa_session, id="job-a", company="Alpha")
        jobs, total = repo.list_jobs(sort_by="bogus_column", sort_dir="sideways")
        assert total == 1
        assert len(jobs) == 1

    def test_no_pagination_returns_all(self, sa_session, repo):
        _add(sa_session, id="job-a")
        _add(sa_session, id="job-b")
        jobs, total = repo.list_jobs()
        assert total == 2
        assert len(jobs) == 2

    def test_excludes_deleted(self, sa_session, repo):
        _add(sa_session, id="job-a", deleted=0)
        _add(sa_session, id="job-b", deleted=1)
        jobs, total = repo.list_jobs()
        assert total == 1


# ── create / get_by_id / upsert ──────────────────────────────────

class TestCreateAndById:
    def test_create_job(self, repo):
        result = repo.create_job("https://example.com/abc", title="Foo",
                                 notes="[]", links="[]", source="api")
        assert result["url"] == "https://example.com/abc"
        assert result["status"] == "imported"
        assert result["title"] == "Foo"

    def test_create_job_defaults(self, sa_session, repo):
        result = repo.create_job("https://example.com/def")
        assert result["url"] == "https://example.com/def"
        row = sa_session.query(JobModel).filter(JobModel.id == result["id"]).first()
        assert row.source == "api"
        assert row.notes == "[]"
        assert row.links == "[]"

    def test_get_by_id(self, sa_session, repo):
        m = _add(sa_session, id="job-1")
        result = repo.get_by_id(m.id)
        assert result["id"] == m.id

    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id("nope") is None

    def test_upsert_insert_no_company(self, repo):
        result = repo.upsert({"id": "job-u", "url": "https://example.com/u"})
        assert result["id"] == "job-u"

    def test_get_processing_items_empty(self, repo):
        assert repo.get_processing_items() == []


# ── set_deleted_by_url / lifecycle ───────────────────────────────

class TestSetDeletedAndLifecycle:
    def test_set_deleted_by_url_no_exclude(self, sa_session, repo):
        _add(sa_session, id="job-a", url="https://same.com")
        _add(sa_session, id="job-b", url="https://same.com")
        count = repo.set_deleted_by_url("https://same.com")
        assert count == 2

    def test_set_deleted_by_url_no_match(self, repo):
        assert repo.set_deleted_by_url("https://missing.com") == 0

    def test_pending_count(self, sa_session, repo):
        _add(sa_session, id="job-a", status="pending")
        _add(sa_session, id="job-b", status="imported")
        assert repo.get_pending_count() == 1

    def test_list_by_status(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", status="queued")
        _add(sa_session, id="job-b", status="processing")
        result = repo.list_by_status("queued")
        assert len(result) == 1
        assert result[0]["id"] == m1.id

    def test_list_by_status_empty(self, repo):
        assert repo.list_by_status("queued") == []

    def test_processing_count(self, sa_session, repo):
        _add(sa_session, id="job-a", status="processing")
        _add(sa_session, id="job-b", status="queued")
        assert repo.get_processing_count() == 1

    def test_queued_count(self, sa_session, repo):
        _add(sa_session, id="job-a", status="queued")
        _add(sa_session, id="job-b", status="pending")
        assert repo.get_queued_count() == 1

    def test_update_status_with_extra(self, sa_session, repo):
        m = _add(sa_session, id="job-a", status="queued")
        assert repo.update_status(m.id, "processing", error="boom") is True
        row = sa_session.query(JobModel).filter(JobModel.id == m.id).first()
        assert row.status == "processing"
        assert row.error == "boom"

    def test_pick_queued_item(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", status="queued", queue_order=2)
        m2 = _add(sa_session, id="job-b", status="queued", queue_order=1)
        result = repo.pick_queued_item()
        assert result["id"] == m2.id
        assert result["status"] == "processing"

    def test_pick_queued_item_none(self, repo):
        assert repo.pick_queued_item() is None

    def test_get_processing_items(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", status="processing")
        _add(sa_session, id="job-b", status="queued")
        items = repo.get_processing_items()
        assert len(items) == 1
        assert items[0]["id"] == m1.id


# ── updated_at auto-bump ─────────────────────────────────────────

class TestUpdatedAtAutoBump:
    def test_update_fields_bumps_updated_at(self, sa_session, repo):
        m = _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:00")
        repo.update_fields(m.id, company="Acme")
        row = sa_session.query(JobModel).filter(JobModel.id == m.id).first()
        assert row.updated_at != "2026-07-27T10:00:00"

    def test_update_fields_honours_explicit_updated_at(self, sa_session, repo):
        m = _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:00")
        repo.update_fields(m.id, company="Acme", updated_at="2026-07-28T10:00:00")
        row = sa_session.query(JobModel).filter(JobModel.id == m.id).first()
        assert row.updated_at == "2026-07-28T10:00:00"

    def test_update_status_bumps_updated_at(self, sa_session, repo):
        m = _add(sa_session, id="job-a", status="queued", updated_at="2026-07-27T10:00:00")
        repo.update_status(m.id, "processing")
        row = sa_session.query(JobModel).filter(JobModel.id == m.id).first()
        assert row.updated_at != "2026-07-27T10:00:00"

    def test_pick_queued_item_bumps_updated_at(self, sa_session, repo):
        m = _add(sa_session, id="job-a", status="queued", updated_at="2026-07-27T10:00:00")
        repo.pick_queued_item()
        row = sa_session.query(JobModel).filter(JobModel.id == m.id).first()
        assert row.updated_at != "2026-07-27T10:00:00"

    def test_mark_deleted_bumps_updated_at(self, sa_session, repo):
        m = _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:00")
        repo.mark_deleted(m.id)
        row = sa_session.query(JobModel).filter(JobModel.id == m.id).first()
        assert row.updated_at != "2026-07-27T10:00:00"
        assert row.deleted == 1

    def test_mark_rescoring_bumps_updated_at(self, sa_session, repo):
        m = _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:00")
        repo.mark_rescoring(m.id, True)
        row = sa_session.query(JobModel).filter(JobModel.id == m.id).first()
        assert row.updated_at != "2026-07-27T10:00:00"
        assert row.rescoring == 1

    def test_update_workflow_log_bumps_updated_at(self, sa_session, repo):
        m = _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:00")
        repo.update_workflow_log(m.id, "[]")
        row = sa_session.query(JobModel).filter(JobModel.id == m.id).first()
        assert row.updated_at != "2026-07-27T10:00:00"

    def test_upsert_update_bumps_updated_at(self, sa_session, repo):
        m = _add(sa_session, id="job-a", url="https://example.com/a", updated_at="2026-07-27T10:00:00")
        repo.upsert({"id": "job-a", "company": "Acme"})
        row = sa_session.query(JobModel).filter(JobModel.id == "job-a").first()
        assert row.updated_at != "2026-07-27T10:00:00"
        assert row.company == "Acme"

    def test_set_deleted_by_url_bumps_updated_at(self, sa_session, repo):
        m = _add(sa_session, id="job-a", url="https://same.com", updated_at="2026-07-27T10:00:00")
        repo.set_deleted_by_url("https://same.com")
        row = sa_session.query(JobModel).filter(JobModel.id == m.id).first()
        assert row.updated_at != "2026-07-27T10:00:00"
        assert row.deleted == 1


# ── search_jobs ──────────────────────────────────────────────────

class TestSearchJobs:
    def test_query_filter(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", title="Backend Engineer", company="Alpha")
        _add(sa_session, id="job-b", title="Frontend Dev", company="Beta")
        rows, total = repo.search_jobs(query="engineer")
        assert total == 1
        assert rows[0]["id"] == m1.id

    def test_query_filter_matches_url(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", title="Backend Engineer", url="https://nl.linkedin.com/jobs/view/abc123")
        _add(sa_session, id="job-b", title="Frontend Dev", url="https://www.indeed.com/xyz")
        rows, total = repo.search_jobs(query="nl.linkedin.com/jobs/view/abc123")
        assert total == 1
        assert rows[0]["id"] == m1.id

    def test_processing_status(self, sa_session, repo):
        _add(sa_session, id="job-a", status="processing")
        m2 = _add(sa_session, id="job-b", status="queued")
        rows, total = repo.search_jobs(processing_status="queued")
        assert total == 1
        assert rows[0]["id"] == m2.id

    def test_company_id(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", company_id="00000000-0000-0000-0000-000000000007")
        _add(sa_session, id="job-b", company_id="00000000-0000-0000-0000-000000000008")
        rows, total = repo.search_jobs(company_id="00000000-0000-0000-0000-000000000007")
        assert total == 1
        assert rows[0]["id"] == m1.id

    def test_remote_true(self, sa_session, repo):
        _add(sa_session, id="job-a", work_types=["Remote"])
        _add(sa_session, id="job-b", work_types=["On-site"])
        rows, total = repo.search_jobs(remote=True)
        assert total == 1
        assert rows[0]["work_types"] == ["Remote"]

    def test_remote_false(self, sa_session, repo):
        _add(sa_session, id="job-a", work_types=["Remote"])
        _add(sa_session, id="job-b", work_types=["On-site"])
        rows, total = repo.search_jobs(remote=False)
        assert total == 1
        assert rows[0]["work_types"] == ["On-site"]

    def test_remote_true_is_exact_token(self, sa_session, repo):
        _add(sa_session, id="job-a", work_types=["Remote Work"])
        _add(sa_session, id="job-b", work_types=["Remote"])
        rows, total = repo.search_jobs(remote=True)
        assert total == 1
        assert rows[0]["id"] == "job-b"

    def test_visa_true(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", visa="US")
        _add(sa_session, id="job-b", visa="")
        rows, total = repo.search_jobs(visa=True)
        assert total == 1
        assert rows[0]["id"] == m1.id

    def test_visa_false(self, sa_session, repo):
        _add(sa_session, id="job-a", visa="US")
        _add(sa_session, id="job-b", visa="")
        _add(sa_session, id="job-c", visa=None)
        rows, total = repo.search_jobs(visa=False)
        assert total == 2

    def test_score_bounds(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", overall_score=80, fit_score=70, success_score=60)
        _add(sa_session, id="job-b", overall_score=50, fit_score=40, success_score=30)
        rows, total = repo.search_jobs(
            overall_score_min=60, overall_score_max=90,
            fit_score_min=65, fit_score_max=75,
            success_score_min=55, success_score_max=65,
        )
        assert total == 1
        assert rows[0]["id"] == m1.id

    def test_sort_and_order(self, sa_session, repo):
        _add(sa_session, id="job-a", title="A", overall_score=40)
        _add(sa_session, id="job-b", title="B", overall_score=90)
        rows, total = repo.search_jobs(sort="overall_score", order="asc")
        assert [r["overall_score"] for r in rows] == [40, 90]

    def test_sort_score_desc_nulls_last(self, sa_session, repo):
        _add(sa_session, id="job-a", title="A", overall_score=90)
        _add(sa_session, id="job-null", title="N")
        _add(sa_session, id="job-b", title="B", overall_score=40)
        rows, total = repo.search_jobs(sort="overall_score", order="desc")
        assert [r["overall_score"] for r in rows] == [90, 40, None]

    def test_sort_score_asc_nulls_last(self, sa_session, repo):
        _add(sa_session, id="job-a", title="A", overall_score=90)
        _add(sa_session, id="job-null", title="N")
        _add(sa_session, id="job-b", title="B", overall_score=40)
        rows, total = repo.search_jobs(sort="overall_score", order="asc")
        assert [r["overall_score"] for r in rows] == [40, 90, None]

    def test_sort_overall_tiebroken_by_success_then_fit_desc(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=80, success_score=70, fit_score=60)
        _add(sa_session, id="job-b", overall_score=80, success_score=70, fit_score=90)
        _add(sa_session, id="job-c", overall_score=80, success_score=90, fit_score=10)
        rows, total = repo.search_jobs(sort="overall_score", order="desc")
        assert [r["id"] for r in rows] == ["job-c", "job-b", "job-a"]

    def test_sort_fit_tiebroken_by_overall_then_success(self, sa_session, repo):
        _add(sa_session, id="job-a", fit_score=70, overall_score=60, success_score=50)
        _add(sa_session, id="job-b", fit_score=70, overall_score=80, success_score=20)
        _add(sa_session, id="job-c", fit_score=70, overall_score=80, success_score=90)
        rows, total = repo.search_jobs(sort="fit_score", order="desc")
        assert [r["id"] for r in rows] == ["job-c", "job-b", "job-a"]

    def test_sort_fallback_and_pagination(self, sa_session, repo):
        for i in range(5):
            _add(sa_session, id=f"job-{i}")
        rows, total = repo.search_jobs(sort="bogus", order="up", page=1, page_size=2)
        assert total == 5
        assert len(rows) == 2


# ── search_jobs_cursor ───────────────────────────────────────────

class TestSearchJobsCursor:
    def test_basic_no_more(self, sa_session, repo):
        _add(sa_session, id="job-a", title="Alpha", updated_at="2026-07-27T10:00:01")
        _add(sa_session, id="job-b", title="Beta", updated_at="2026-07-27T10:00:02")
        items, total, next_cursor, has_more = repo.search_jobs_cursor(page_size=10)
        assert total == 2
        assert len(items) == 2
        assert has_more is False
        assert next_cursor is None

    def test_has_more(self, sa_session, repo):
        for i in range(5):
            _add(sa_session, id=f"job-{i}", updated_at=f"2026-07-27T10:00:{i:02d}")
        items, total, next_cursor, has_more = repo.search_jobs_cursor(page_size=2, sort="updated_at")
        assert len(items) == 2
        assert has_more is True

    def test_query_matches_url(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", title="Alpha", url="https://careers.alpha.com/role/123")
        _add(sa_session, id="job-b", title="Beta", url="https://careers.beta.com/role/456")
        items, total, _, _ = repo.search_jobs_cursor(query="careers.alpha.com/role/123")
        assert total == 1
        assert items[0]["id"] == m1.id

    def test_cursor_desc(self, sa_session, repo):
        for i in range(5):
            _add(sa_session, id=f"job-{i}", updated_at=f"2026-07-27T10:00:{i:02d}")
        _, _, first_cursor, _ = repo.search_jobs_cursor(page_size=2, sort="updated_at", order="desc")
        items, total, _, has_more = repo.search_jobs_cursor(
            page_size=2, sort="updated_at", order="desc", cursor=first_cursor
        )
        assert len(items) == 2
        boundary = first_cursor.rsplit("|", 1)[0]
        assert all(i["updated_at"] < boundary for i in items)
        assert has_more is True

    def test_cursor_asc(self, sa_session, repo):
        for i in range(5):
            _add(sa_session, id=f"job-{i}", updated_at=f"2026-07-27T10:00:{i:02d}")
        _, _, first_cursor, _ = repo.search_jobs_cursor(page_size=2, sort="updated_at", order="asc")
        items, total, _, has_more = repo.search_jobs_cursor(
            page_size=2, sort="updated_at", order="asc", cursor=first_cursor
        )
        assert len(items) == 2
        boundary = first_cursor.rsplit("|", 1)[0]
        assert all(i["updated_at"] > boundary for i in items)

    def test_cursor_score_desc_nulls_last_reaches_null_tail(self, sa_session, repo):
        _add(sa_session, id="job-1", overall_score=90)
        _add(sa_session, id="job-2", overall_score=40)
        _add(sa_session, id="job-null-a")
        _add(sa_session, id="job-null-b")
        _add(sa_session, id="job-null-c")

        items, total, cursor, has_more = repo.search_jobs_cursor(
            page_size=2, sort="overall_score", order="desc"
        )
        assert total == 5
        assert [i["overall_score"] for i in items] == [90, 40]
        assert has_more is True

        items, total, cursor2, has_more = repo.search_jobs_cursor(
            page_size=2, sort="overall_score", order="desc", cursor=cursor
        )
        assert [i["overall_score"] for i in items] == [None, None]
        assert has_more is True

        items, total, cursor3, has_more = repo.search_jobs_cursor(
            page_size=2, sort="overall_score", order="desc", cursor=cursor2
        )
        assert [i["overall_score"] for i in items] == [None]
        assert has_more is False
        assert cursor3 is None

    def test_cursor_score_asc_nulls_last(self, sa_session, repo):
        _add(sa_session, id="job-1", overall_score=90)
        _add(sa_session, id="job-2", overall_score=40)
        _add(sa_session, id="job-null-a")
        _add(sa_session, id="job-null-b")
        items, total, _, _ = repo.search_jobs_cursor(
            page_size=10, sort="overall_score", order="asc"
        )
        assert total == 4
        assert [i["overall_score"] for i in items] == [40, 90, None, None]

    def test_cursor_tie_values_tiebroken_by_id_desc(self, sa_session, repo):
        _add(sa_session, id="job-1", overall_score=50)
        _add(sa_session, id="job-2", overall_score=50)
        _add(sa_session, id="job-3", overall_score=50)
        items, total, _, _ = repo.search_jobs_cursor(
            page_size=10, sort="overall_score", order="desc"
        )
        assert total == 3
        assert [i["id"] for i in items] == ["job-3", "job-2", "job-1"]

    def test_cursor_overall_tiebroken_by_success_then_fit_desc(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=80, success_score=70, fit_score=60)
        _add(sa_session, id="job-b", overall_score=80, success_score=70, fit_score=90)
        _add(sa_session, id="job-c", overall_score=80, success_score=90, fit_score=10)
        items, total, _, _ = repo.search_jobs_cursor(
            page_size=10, sort="overall_score", order="desc"
        )
        assert total == 3
        assert [i["id"] for i in items] == ["job-c", "job-b", "job-a"]

    def test_cursor_overall_tiebroken_asc(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=80, success_score=70, fit_score=60)
        _add(sa_session, id="job-b", overall_score=80, success_score=70, fit_score=90)
        _add(sa_session, id="job-c", overall_score=80, success_score=90, fit_score=10)
        items, total, _, _ = repo.search_jobs_cursor(
            page_size=10, sort="overall_score", order="asc"
        )
        assert [i["id"] for i in items] == ["job-a", "job-b", "job-c"]

    def test_cursor_fit_sort_tiebroken_by_overall_then_success(self, sa_session, repo):
        _add(sa_session, id="job-a", fit_score=70, overall_score=60, success_score=50)
        _add(sa_session, id="job-b", fit_score=70, overall_score=80, success_score=20)
        _add(sa_session, id="job-c", fit_score=70, overall_score=80, success_score=90)
        items, total, _, _ = repo.search_jobs_cursor(
            page_size=10, sort="fit_score", order="desc"
        )
        assert total == 3
        assert [i["id"] for i in items] == ["job-c", "job-b", "job-a"]

    def test_cursor_success_sort_tiebroken_by_overall_then_fit(self, sa_session, repo):
        _add(sa_session, id="job-a", success_score=70, overall_score=60, fit_score=50)
        _add(sa_session, id="job-b", success_score=70, overall_score=80, fit_score=20)
        _add(sa_session, id="job-c", success_score=70, overall_score=80, fit_score=90)
        items, total, _, _ = repo.search_jobs_cursor(
            page_size=10, sort="success_score", order="desc"
        )
        assert total == 3
        assert [i["id"] for i in items] == ["job-c", "job-b", "job-a"]

    def test_cursor_overall_tiebreak_across_pages(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=80, success_score=70, fit_score=60)
        _add(sa_session, id="job-b", overall_score=80, success_score=70, fit_score=90)
        _add(sa_session, id="job-c", overall_score=80, success_score=90, fit_score=10)
        items, total, cursor, has_more = repo.search_jobs_cursor(
            page_size=2, sort="overall_score", order="desc"
        )
        assert [i["id"] for i in items] == ["job-c", "job-b"]
        assert has_more is True
        items, total, cursor2, has_more = repo.search_jobs_cursor(
            page_size=2, sort="overall_score", order="desc", cursor=cursor
        )
        assert [i["id"] for i in items] == ["job-a"]
        assert has_more is False
        assert cursor2 is None

    def test_filters_with_cursor(self, sa_session, repo):
        ids = [f"job-{i}" for i in range(3)]
        for i in range(3):
            _add(sa_session, id=ids[i], status="processing", visa="US",
                 updated_at=f"2026-07-27T10:00:{i:02d}")
        items, total, next_cursor, has_more = repo.search_jobs_cursor(
            page_size=2, job_ids=ids, visa=True,
            sort="updated_at", order="asc",
        )
        assert total == 3
        assert len(items) == 2
        assert has_more is True

    def test_job_ids_filter(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:01")
        _add(sa_session, id="job-b", updated_at="2026-07-27T10:00:02")
        items, total, _, _ = repo.search_jobs_cursor(job_ids=[m1.id])
        assert total == 1
        assert items[0]["id"] == m1.id

    def test_job_ids_empty_excludes_everything(self, sa_session, repo):
        _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:01")
        _add(sa_session, id="job-b", updated_at="2026-07-27T10:00:02")
        items, total, _, _ = repo.search_jobs_cursor(job_ids=[])
        assert total == 0
        assert items == []

    def test_all_branches(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", title="Engineer", company="Alpha", company_id="00000000-0000-0000-0000-000000000007",
                  work_types=["Remote"], visa="US", overall_score=85, fit_score=80,
                  success_score=70, updated_at="2026-07-27T10:00:01")
        _add(sa_session, id="job-b", title="Other", company="Beta", company_id="00000000-0000-0000-0000-000000000008",
             work_types=["On-site"], visa="", overall_score=40, fit_score=30,
             success_score=20, updated_at="2026-07-27T10:00:02")
        items, total, _, has_more = repo.search_jobs_cursor(
            query="engineer", job_ids=[m1.id], company_id="00000000-0000-0000-0000-000000000007",
            remote=True, visa=True,
            overall_score_min=80, overall_score_max=90,
            fit_score_min=70, fit_score_max=90,
            success_score_min=60, success_score_max=80,
            sort="title", order="asc",
        )
        assert total == 1
        assert items[0]["id"] == m1.id
        assert has_more is False

    def test_score_min_only(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", overall_score=70, fit_score=80, success_score=70,
                  updated_at="2026-07-27T10:00:01")
        _add(sa_session, id="job-b", overall_score=30, fit_score=30, success_score=20,
             updated_at="2026-07-27T10:00:02")
        items, total, _, _ = repo.search_jobs_cursor(
            overall_score_min=60, overall_score_max=80,
            fit_score_min=10, success_score_min=10,
        )
        assert total == 1
        assert items[0]["id"] == m1.id

    def test_visa_false_and_remote_false(self, sa_session, repo):
        _add(sa_session, id="job-a", visa="US", work_types=["Remote"],
             updated_at="2026-07-27T10:00:01")
        m2 = _add(sa_session, id="job-b", visa="", work_types=["On-site"],
                  updated_at="2026-07-27T10:00:02")
        m3 = _add(sa_session, id="job-c", visa=None, work_types=["On-site"],
                  updated_at="2026-07-27T10:00:03")
        items, total, _, _ = repo.search_jobs_cursor(visa=False, remote=False)
        assert total == 2
        assert {i["id"] for i in items} == {m2.id, m3.id}

    def test_empty(self, repo):
        items, total, next_cursor, has_more = repo.search_jobs_cursor()
        assert items == []
        assert total == 0
        assert next_cursor is None
        assert has_more is False


class TestSearchJobsCursorLocation:
    def test_matches_substring_case_insensitive(self, sa_session, repo):
        _add(sa_session, id="job-berlin", location="Berlin, Germany")
        _add(sa_session, id="job-amsterdam", location="Amsterdam, Netherlands")
        _add(sa_session, id="job-hamburg", location="Hamburg, Germany")

        items, total, _, _ = repo.search_jobs_cursor(location="germany")

        assert total == 2
        assert {i["id"] for i in items} == {"job-berlin", "job-hamburg"}

    def test_empty_location_is_noop(self, sa_session, repo):
        _add(sa_session, id="job-berlin", location="Berlin")
        _add(sa_session, id="job-amsterdam", location="Amsterdam")

        items, total, _, _ = repo.search_jobs_cursor(location="")

        assert total == 2

    def test_no_match(self, sa_session, repo):
        _add(sa_session, id="job-berlin", location="Berlin")

        items, total, _, _ = repo.search_jobs_cursor(location="Madrid")

        assert total == 0
        assert items == []

    def test_combines_with_other_filters(self, sa_session, repo):
        _add(sa_session, id="job-a", location="Berlin", work_types=["Remote"])
        _add(sa_session, id="job-b", location="Berlin", work_types=["On-site"])
        _add(sa_session, id="job-c", location="Amsterdam", work_types=["Remote"])

        items, total, _, _ = repo.search_jobs_cursor(location="berlin", remote=True)

        assert total == 1
        assert items[0]["id"] == "job-a"


class TestSearchJobsCursorStatusSort:
    def _jobs_and_executions(self, sa_session):
        _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:01")
        _add(sa_session, id="job-b", updated_at="2026-07-27T10:00:02")
        _add(sa_session, id="job-c", updated_at="2026-07-27T10:00:03")
        _add_execution(sa_session, "job-a", "failed", "2026-07-27T10:00:10")
        _add_execution(sa_session, "job-a", "completed", "2026-07-27T10:00:11")
        _add_execution(sa_session, "job-b", "queued", "2026-07-27T10:00:12")
        return {"job-a": "completed", "job-b": "queued"}

    def test_sorts_by_latest_execution_status_unprocessed_last(self, sa_session, repo):
        status_lookup = self._jobs_and_executions(sa_session)

        items, total, _, _ = repo.search_jobs_cursor(
            sort="status", order="asc", status_lookup=status_lookup
        )

        assert total == 3
        assert [i["id"] for i in items] == ["job-a", "job-b", "job-c"]

    def test_desc_reverses_statuses_but_unprocessed_still_last(self, sa_session, repo):
        status_lookup = self._jobs_and_executions(sa_session)

        items, total, _, _ = repo.search_jobs_cursor(
            sort="status", order="desc", status_lookup=status_lookup
        )

        assert total == 3
        assert [i["id"] for i in items] == ["job-b", "job-a", "job-c"]

    def test_groups_same_status_and_ties_by_id(self, sa_session, repo):
        _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:01")
        _add(sa_session, id="job-b", updated_at="2026-07-27T10:00:02")
        _add_execution(sa_session, "job-a", "completed", "2026-07-27T10:00:10")
        _add_execution(sa_session, "job-b", "completed", "2026-07-27T10:00:11")

        items, total, _, _ = repo.search_jobs_cursor(
            sort="status", order="asc",
            status_lookup={"job-a": "completed", "job-b": "completed"},
        )

        assert total == 2
        assert [i["id"] for i in items] == ["job-a", "job-b"]

    def test_cursor_pagination_no_skip_no_dupe(self, sa_session, repo):
        status_lookup = self._jobs_and_executions(sa_session)

        _, _, first_cursor, _ = repo.search_jobs_cursor(
            page_size=1, sort="status", order="desc", status_lookup=status_lookup
        )
        page2, _, second_cursor, _ = repo.search_jobs_cursor(
            page_size=1, sort="status", order="desc", cursor=first_cursor,
            status_lookup=status_lookup,
        )
        page3, _, _, has_more = repo.search_jobs_cursor(
            page_size=1, sort="status", order="desc", cursor=second_cursor,
            status_lookup=status_lookup,
        )

        ids = [p[0]["id"] for p in (page2, page3)]
        assert ids == ["job-a", "job-c"]
        assert has_more is False

    def test_unprocessed_jobs_reachable_across_cursor(self, sa_session, repo):
        _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:01")
        _add(sa_session, id="job-b", updated_at="2026-07-27T10:00:02")
        _add_execution(sa_session, "job-a", "completed", "2026-07-27T10:00:10")

        status_lookup = {"job-a": "completed"}
        _, _, first_cursor, _ = repo.search_jobs_cursor(
            page_size=1, sort="status", order="desc", status_lookup=status_lookup
        )
        page2, total, _, has_more = repo.search_jobs_cursor(
            page_size=1, sort="status", order="desc", cursor=first_cursor,
            status_lookup=status_lookup,
        )

        assert total == 2
        assert [i["id"] for i in page2] == ["job-b"]
        assert has_more is False


class TestSearchJobsCursorExclude:
    def test_exclude_job_ids(self, sa_session, repo):
        _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:01")
        m2 = _add(sa_session, id="job-b", updated_at="2026-07-27T10:00:02")
        _add(sa_session, id="job-c", updated_at="2026-07-27T10:00:03")

        items, total, _, _ = repo.search_jobs_cursor(exclude_job_ids=[m2.id])

        assert total == 2
        assert {i["id"] for i in items} == {"job-a", "job-c"}

    def test_exclude_empty_list_is_noop(self, sa_session, repo):
        _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:01")
        _add(sa_session, id="job-b", updated_at="2026-07-27T10:00:02")

        items, total, _, _ = repo.search_jobs_cursor(exclude_job_ids=[])

        assert total == 2

    def test_exclude_all(self, sa_session, repo):
        _add(sa_session, id="job-a", updated_at="2026-07-27T10:00:01")

        items, total, _, _ = repo.search_jobs_cursor(exclude_job_ids=["job-a"])

        assert total == 0
        assert items == []


# ── search_jobs_cursor created_date (today / yesterday / week / month) ──

class TestSearchJobsCursorCreatedDate:
    @staticmethod
    def _iso(dt: datetime) -> str:
        return dt.replace(tzinfo=None).isoformat()

    @staticmethod
    def _space(dt: datetime) -> str:
        # str(datetime) layout, as stored for fresh inserts.
        return str(dt.replace(tzinfo=None))

    def _now(self):
        return datetime.now(UTC)

    def test_today_matches_space_separated_fresh_insert_format(self, sa_session, repo):
        today_start = self._now().replace(hour=0, minute=0, second=0, microsecond=0)
        _add(sa_session, id="job-space", created_at=self._space(today_start + timedelta(hours=11)))
        _add(sa_session, id="job-old", created_at=self._space(today_start - timedelta(days=3)))

        items, total, _, _ = repo.search_jobs_cursor(created_date="today")
        assert total == 1
        assert items[0]["id"] == "job-space"

    def test_today_includes_start_of_day_and_excludes_yesterday(self, sa_session, repo):
        now = self._now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_mid = today_start.replace(hour=12)
        yesterday = today_start - timedelta(days=1) + timedelta(hours=8)

        _add(sa_session, id="job-today", created_at=self._iso(today_mid))
        _add(sa_session, id="job-yesterday", created_at=self._iso(yesterday))

        items, total, _, _ = repo.search_jobs_cursor(created_date="today")
        assert total == 1
        assert items[0]["id"] == "job-today"

    def test_yesterday_excludes_today(self, sa_session, repo):
        today_start = self._now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_mid = today_start - timedelta(days=1) + timedelta(hours=12)
        _add(sa_session, id="job-yesterday", created_at=self._iso(yesterday_mid))
        _add(sa_session, id="job-today", created_at=self._iso(today_start + timedelta(hours=6)))

        items, total, _, _ = repo.search_jobs_cursor(created_date="yesterday")
        assert total == 1
        assert items[0]["id"] == "job-yesterday"

    def test_week_includes_5_days_ago_excludes_10_days_ago(self, sa_session, repo):
        now = self._now()
        _add(sa_session, id="job-in", created_at=self._iso(now - timedelta(days=5)))
        _add(sa_session, id="job-out", created_at=self._iso(now - timedelta(days=10)))

        items, total, _, _ = repo.search_jobs_cursor(created_date="week")
        assert total == 1
        assert items[0]["id"] == "job-in"

    def test_month_includes_20_days_ago_excludes_40_days_ago(self, sa_session, repo):
        now = self._now()
        _add(sa_session, id="job-in", created_at=self._iso(now - timedelta(days=20)))
        _add(sa_session, id="job-out", created_at=self._iso(now - timedelta(days=40)))

        items, total, _, _ = repo.search_jobs_cursor(created_date="month")
        assert total == 1
        assert items[0]["id"] == "job-in"

    def test_unknown_created_date_is_noop(self, sa_session, repo):
        _add(sa_session, id="job-a", created_at=self._iso(self._now() - timedelta(days=400)))
        _add(sa_session, id="job-b", created_at=self._iso(self._now()))

        items, total, _, _ = repo.search_jobs_cursor(created_date="all-time")
        assert total == 2

    def test_none_created_date_is_noop(self, sa_session, repo):
        _add(sa_session, id="job-a", created_at=self._iso(self._now() - timedelta(days=400)))
        _add(sa_session, id="job-b", created_at=self._iso(self._now()))

        items, total, _, _ = repo.search_jobs_cursor()
        assert total == 2


# ── score_rank (competition ranking: overall, success, fit) ─────

class TestScoreRank:
    def test_top_score_ranks_first(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-b", overall_score=40)
        assert repo.score_rank(m1.id) == 1

    def test_ranks_after_higher_scores(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=90)
        m2 = _add(sa_session, id="job-b", overall_score=40)
        _add(sa_session, id="job-c", overall_score=70)
        assert repo.score_rank(m2.id) == 3

    def test_same_overall_success_breaks_tie(self, sa_session, repo):
        m_high = _add(sa_session, id="job-high", overall_score=80, success_score=90)
        _add(sa_session, id="job-low", overall_score=80, success_score=60)
        assert repo.score_rank(m_high.id) == 1
        assert repo.score_rank(_add(sa_session, id="job-low2", overall_score=80, success_score=60).id) == 2

    def test_same_overall_and_success_fit_breaks_tie(self, sa_session, repo):
        m_high = _add(sa_session, id="job-high", overall_score=80, success_score=70, fit_score=90)
        m_low = _add(sa_session, id="job-low", overall_score=80, success_score=70, fit_score=50)
        assert repo.score_rank(m_high.id) == 1
        assert repo.score_rank(m_low.id) == 2

    def test_all_scores_equal_share_rank(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=80, success_score=70, fit_score=60)
        m_b = _add(sa_session, id="job-b", overall_score=80, success_score=70, fit_score=60)
        m_c = _add(sa_session, id="job-c", overall_score=80, success_score=70, fit_score=60)
        # Competition ranking: all three share rank 1.
        assert repo.score_rank(m_c.id) == 1
        assert repo.score_rank(m_b.id) == 1

    def test_null_score_ranks_after_all_scored(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-b", overall_score=40)
        m_null = _add(sa_session, id="job-null")
        assert repo.score_rank(m_null.id) == 3

    def test_null_score_rank_when_no_scored_jobs(self, sa_session, repo):
        m_null = _add(sa_session, id="job-null")
        assert repo.score_rank(m_null.id) == 1

    def test_excludes_deleted_jobs(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-b", overall_score=40, deleted=1)
        assert repo.score_rank(m1.id) == 1

    def test_missing_job_returns_none(self, repo):
        assert repo.score_rank("does-not-exist") is None


# ── ranks_by_ids ─────────────────────────────────────────────────

class TestRanksByIds:
    def test_distinct_scores_rank_sequentially(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-b", overall_score=70)
        _add(sa_session, id="job-c", overall_score=50)
        ranks = repo.ranks_by_ids(["job-a", "job-b", "job-c"])
        assert ranks == {"job-a": 1, "job-b": 2, "job-c": 3}

    def test_equal_scores_share_rank(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=80, success_score=70, fit_score=60)
        _add(sa_session, id="job-b", overall_score=80, success_score=70, fit_score=60)
        _add(sa_session, id="job-c", overall_score=50, success_score=50, fit_score=50)
        # job-a and job-b tie for rank 1 (competition ranking); job-c is next.
        ranks = repo.ranks_by_ids(["job-a", "job-b", "job-c"])
        assert ranks == {"job-a": 1, "job-b": 1, "job-c": 3}

    def test_same_overall_differs_on_tiebreak_columns(self, sa_session, repo):
        # RANK() orders by overall, then success, then fit — equal on all three
        # share a rank; differing on success/fit do not.
        _add(sa_session, id="job-a", overall_score=80, success_score=90, fit_score=10)
        _add(sa_session, id="job-b", overall_score=80, success_score=70, fit_score=90)
        _add(sa_session, id="job-c", overall_score=80, success_score=70, fit_score=60)
        ranks = repo.ranks_by_ids(["job-a", "job-b", "job-c"])
        assert ranks == {"job-a": 1, "job-b": 2, "job-c": 3}

    def test_null_scores_rank_last(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-b", overall_score=40)
        _add(sa_session, id="job-null")
        ranks = repo.ranks_by_ids(["job-a", "job-b", "job-null"])
        assert ranks == {"job-a": 1, "job-b": 2, "job-null": 3}

    def test_null_scores_share_rank(self, sa_session, repo):
        _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-null-1")
        _add(sa_session, id="job-null-2")
        # Both unscored jobs tie for last rank.
        ranks = repo.ranks_by_ids(["job-a", "job-null-1", "job-null-2"])
        assert ranks == {"job-a": 1, "job-null-1": 2, "job-null-2": 2}

    def test_excludes_deleted_jobs(self, sa_session, repo):
        m1 = _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-b", overall_score=40, deleted=1)
        _add(sa_session, id="job-c", overall_score=30)
        ranks = repo.ranks_by_ids([m1.id, "job-b", "job-c"])
        assert ranks == {m1.id: 1, "job-c": 2}

    def test_ranks_are_absolute_over_full_set_not_just_requested(self, sa_session, repo):
        # ranks_by_ids ranks over all non-deleted jobs; requesting a subset still
        # yields their true position in the full ordering.
        _add(sa_session, id="job-a", overall_score=90)
        _add(sa_session, id="job-b", overall_score=70)
        _add(sa_session, id="job-c", overall_score=50)
        _add(sa_session, id="job-d", overall_score=30)
        ranks = repo.ranks_by_ids(["job-c", "job-b"])
        assert ranks == {"job-b": 2, "job-c": 3}

    def test_empty_input_returns_empty_dict(self, repo):
        assert repo.ranks_by_ids([]) == {}


# ── get_by_url_fragment ─────────────────────────────────────────

class TestGetByUrlFragment:
    def test_matches_job_url_containing_fragment(self, sa_session, repo):
        m = _add(
            sa_session,
            id="job-1",
            url="https://www.linkedin.com/jobs/view/4333938709/?trackingId=AAA",
        )
        result = repo.get_by_url_fragment("linkedin.com/jobs/view/4333938709")
        assert result is not None
        assert result["id"] == m.id

    def test_ignores_deleted_jobs(self, sa_session, repo):
        _add(sa_session, id="job-1", deleted=1,
             url="https://www.linkedin.com/jobs/view/4333938709/")
        assert repo.get_by_url_fragment("linkedin.com/jobs/view/4333938709") is None

    def test_returns_none_when_no_match(self, sa_session, repo):
        _add(sa_session, id="job-1", url="https://example.com/jobs/1")
        assert repo.get_by_url_fragment("linkedin.com/jobs/view/1") is None

    def test_returns_none_for_absent_fragment(self, repo):
        assert repo.get_by_url_fragment("linkedin.com/jobs/view/999999") is None


# ── not-found branches ───────────────────────────────────────────

class TestNotFoundBranches:
    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id("missing") is None

    def test_get_by_url_not_found(self, repo):
        assert repo.get_by_url("https://missing.com") is None

    def test_get_id_by_url_not_found(self, repo):
        assert repo.get_id_by_url("https://missing.com") is None

    def test_get_company_id_not_found(self, repo):
        assert repo.get_company_id("missing") is None

    def test_get_company_id_by_id_not_found(self, repo):
        assert repo.get_company_id_by_id("missing") is None