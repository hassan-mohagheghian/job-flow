"""Tests for the job-sources dashboard API and ingestion source linking."""

import uuid

import pytest
from jobs.infrastructure.models.job_model import JobModel, JobSourceModel

from jobs.domain.services.job_source_rules import resolve_source


def _create_source(test_db, domain: str, user_id: str = "test-user", name: str | None = None, **overrides) -> JobSourceModel:
    model = JobSourceModel(
        id=str(uuid.uuid7()),
        user_id=user_id,
        name=name or domain,
        canonical_url=f"https://{domain}",
        normalized_domain=domain,
        is_active=overrides.get("is_active", 1),
    )
    test_db.add(model)
    test_db.commit()
    return model


def _create_job(test_db, url: str, source_site, user_id: str = "test-user", deleted: int = 0) -> JobModel:
    model = JobModel(
        id=str(uuid.uuid7()),
        url=url,
        status="imported",
        deleted=deleted,
        user_id=user_id,
        source_site_id=source_site.id if source_site else None,
        workflow_log="[]",
        locations="[]",
        employment_types='["Full-time"]',
        rescoring=0,
    )
    test_db.add(model)
    test_db.commit()
    return model


@pytest.fixture
def linkedin(test_db):
    return _create_source(test_db, "linkedin.com")


class TestSourceStats:
    def test_counts_live_jobs_per_source(self, client, test_db, linkedin):
        indeed = _create_source(test_db, "indeed.com")
        _create_job(test_db, "https://linkedin.com/1", linkedin)
        _create_job(test_db, "https://linkedin.com/2", linkedin)
        _create_job(test_db, "https://indeed.com/1", indeed)
        _create_job(test_db, "https://nosite", None)

        body = client.get("/api/jobs/sources/stats").json()
        assert body == {
            "total_jobs": 4,
            "total_sources": 2,
            "active_sources": 2,
            "unknown_jobs": 1,
        }

    def test_deleted_jobs_do_not_count(self, client, test_db, linkedin):
        _create_job(test_db, "https://linkedin.com/1", linkedin)
        _create_job(test_db, "https://linkedin.com/2", linkedin, deleted=1)

        body = client.get("/api/jobs/sources/stats").json()
        assert body["total_jobs"] == 1
        assert body["total_sources"] == 1

    def test_empty_dataset(self, client):
        body = client.get("/api/jobs/sources/stats").json()
        assert body == {
            "total_jobs": 0,
            "total_sources": 0,
            "active_sources": 0,
            "unknown_jobs": 0,
        }

    def test_other_users_sources_are_excluded(self, client, test_db):
        other = _create_source(test_db, "other-user-board.com", user_id="someone-else")
        _create_job(test_db, "https://other-user-board.com/1", other, user_id="someone-else")

        body = client.get("/api/jobs/sources/stats").json()
        assert body["total_jobs"] == 0
        assert body["total_sources"] == 0

        listing = client.get("/api/jobs/sources").json()
        assert [i["domain"] for i in listing["items"]] == []


class TestSourceDistribution:
    def test_top_five_and_other(self, client, test_db):
        domains = [f"board{i}.com" for i in range(7)]
        sites = [_create_source(test_db, domain) for domain in domains]
        for site, n_jobs in zip(sites, [9, 8, 7, 6, 5, 4, 3]):
            for i in range(n_jobs):
                _create_job(test_db, f"https://{site.normalized_domain}/job{i}", site)
        _create_job(test_db, "https://nosite", None)

        body = client.get("/api/jobs/sources/distribution").json()
        assert [i["domain"] for i in body["items"]] == [
            "board0.com",
            "board1.com",
            "board2.com",
            "board3.com",
            "board4.com",
        ]
        assert body["other_count"] == 7  # 4 + 3
        assert body["unknown_count"] == 1

    def test_zero_jobs_graceful(self, client):
        body = client.get("/api/jobs/sources/distribution").json()
        assert body == {"items": [], "other_count": 0, "unknown_count": 0}

    def test_limit_param(self, client, test_db):
        a = _create_source(test_db, "a.com")
        b = _create_source(test_db, "b.com")
        _create_job(test_db, "https://a.com/1", a)
        _create_job(test_db, "https://b.com/1", b)

        body = client.get("/api/jobs/sources/distribution?limit=1").json()
        assert len(body["items"]) == 1
        assert body["other_count"] == 1


class TestSourcesList:
    def test_pagination_sort_by_count(self, client, test_db):
        a = _create_source(test_db, "a.com", name="Alpha")
        b = _create_source(test_db, "b.com", name="Beta")
        c = _create_source(test_db, "c.com", name="Gamma")
        _create_job(test_db, "https://a.com/1", a)
        _create_job(test_db, "https://a.com/2", a)
        _create_job(test_db, "https://b.com/1", b)

        body = client.get("/api/jobs/sources?page_size=2").json()
        assert [i["domain"] for i in body["items"]] == ["a.com", "b.com"]
        assert body["pagination"] == {"page": 1, "page_size": 2, "total_items": 3, "total_pages": 2}

        body = client.get("/api/jobs/sources?page=2&page_size=2").json()
        assert [i["domain"] for i in body["items"]] == ["c.com"]
        gamma = body["items"][0]
        assert gamma["job_count"] == 0
        assert gamma["canonical_url"] == "https://c.com"

    def test_sort_name_and_search(self, client, test_db):
        alpha = _create_source(test_db, "alpha.net", name="Alpha.net")
        beta = _create_source(test_db, "beta.net", name="Beta.net")
        _create_job(test_db, "https://beta.net/1", beta)

        body = client.get("/api/jobs/sources?sort=name&order=asc").json()
        assert [i["name"] for i in body["items"]] == ["Alpha.net", "Beta.net"]

        body = client.get("/api/jobs/sources?query=alpha").json()
        assert [i["domain"] for i in body["items"]] == ["alpha.net"]

    def test_sort_last_activity(self, client, test_db):
        # Avoid sorts upstream here; last_activity positions verified live in repo tests
        a = _create_source(test_db, "a.com")
        b = _create_source(test_db, "b.com")
        _create_job(test_db, "https://a.com/1", a)

        body = client.get("/api/jobs/sources?sort=last_activity").json()
        assert body["items"][0]["domain"] == "a.com"
        assert body["items"][0]["last_activity"]

    def test_last_activity_null_when_never(self, client, test_db):
        _create_source(test_db, "empty.com")
        body = client.get("/api/jobs/sources").json()
        assert body["items"][0]["last_activity"] is None

    @pytest.mark.parametrize(
        "params",
        [
            "?sort=bogus",
            "?order=weird",
        ],
    )
    def test_invalid_params_422(self, client, params):
        assert client.get(f"/api/jobs/sources{params}").status_code == 422


class TestIngestionSourceLinking:
    def test_create_job_resolves_source(self, test_db):
        from jobs.infrastructure import SQLAlchemyJobRepository

        repo = SQLAlchemyJobRepository(test_db, user_id="test-user")
        created = repo.create_job(url="https://de.indeed.co.uk/viewjob?jk=abc", source="cli")

        assert created["source_site_id"]
        site = test_db.query(JobSourceModel).filter_by(id=created["source_site_id"]).one()
        assert site.normalized_domain == resolve_source("https://de.indeed.co.uk/viewjob?jk=abc") == "indeed.com"
        assert site.name == "Indeed.com"
        assert site.canonical_url == "https://indeed.com"

    def test_repeated_ingestion_reuses_source(self, test_db):
        from jobs.infrastructure import SQLAlchemyJobRepository

        repo = SQLAlchemyJobRepository(test_db, user_id="test-user")
        first = repo.create_job(url="https://www.linkedin.com/jobs/view/1")
        second = repo.create_job(url="https://www.linkedin.com/jobs/view/2")

        assert first["source_site_id"] == second["source_site_id"]
        assert test_db.query(JobSourceModel).count() == 1
