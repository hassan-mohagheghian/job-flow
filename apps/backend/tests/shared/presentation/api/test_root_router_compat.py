"""Coverage tests for the inline compat routes in shared/presentation/api/root_router.py.

These routes live at the bottom of root_router.py (after the include_router calls)
and are mounted under the /api prefix. They are tested through the ``client``
fixture from tests/conftest.py, which wires a real SQLAlchemy test session via
FastAPI DI dependency overrides.
"""

from unittest.mock import patch

import pytest

from jobs.infrastructure.models.job_model import JobModel
from companies.infrastructure.models.company_model import CompanyModel
from skills.infrastructure.models.skill_model import SkillModel, SkillRelationshipModel
from jobs.infrastructure.models.misc_models import SummaryModel


def _mark_all_jobs_processed(sa_session):
    sa_session.query(JobModel).filter(JobModel.status != "processed").update(
        {"status": "processed"}
    )
    sa_session.commit()


def _mark_all_companies_processed(sa_session):
    sa_session.query(CompanyModel).filter(CompanyModel.status != "processed").update(
        {"status": "processed"}
    )
    sa_session.commit()


def _seed_company(sa_session, name="Co"):
    co = CompanyModel(name=name, user_id="test-user")
    sa_session.add(co)
    sa_session.commit()
    return co.id


# ── summaries / tech-stack ──────────────────────────────────────


def test_summaries_compat(client, sa_session):
    sa_session.add(JobModel(id="job-901", company="SummaryCo", user_id="test-user"))
    sa_session.add(SummaryModel(job_id="job-901", company="SummaryCo", score="A"))
    sa_session.commit()
    resp = client.get("/api/summaries")
    assert resp.status_code == 200
    assert any(r["job_id"] == "job-901" and r["company"] == "SummaryCo" for r in resp.json())


def test_tech_stack_compat(client, sa_session):
    sa_session.add(SkillModel(name="TechStackPy", hidden=0, user_id="test-user"))
    sa_session.add(SkillModel(name="HiddenSkill", hidden=1, user_id="test-user"))
    sa_session.commit()
    resp = client.get("/api/tech-stack")
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert "TechStackPy" in names
    assert "HiddenSkill" not in names


# ── skill relationships ─────────────────────────────────────────


def test_get_skill_relationships_compat(client, sa_session):
    sa_session.add(
        SkillRelationshipModel(
            skill_name="RelReact", related_name="ReactJS", relation_type="similar"
        )
    )
    sa_session.commit()
    resp = client.get("/api/skill-relationships/RelReact")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_skill_relationship_compat(client, sa_session):
    resp = client.post(
        "/api/skill-relationships",
        json={"skill_name": "RelPython", "related_name": "Py", "relation_type": "similar"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "created"}


def test_create_skill_relationship_compat_conflict(client, sa_session):
    body = {"skill_name": "RelDup", "related_name": "Dup", "relation_type": "similar"}
    assert client.post("/api/skill-relationships", json=body).status_code == 200
    resp = client.post("/api/skill-relationships", json=body)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_delete_skill_relationship_compat(client, sa_session):
    rel = SkillRelationshipModel(
        skill_name="RelDel", related_name="Del", relation_type="similar"
    )
    sa_session.add(rel)
    sa_session.commit()
    resp = client.delete(f"/api/skill-relationships/{rel.id}")
    assert resp.status_code == 200
    assert resp.json() == {"status": "deleted"}


# ── job-company link / company reprocess ────────────────────────


def test_link_job_to_company_with_company_id(client, sa_session):
    sa_session.add(JobModel(id="job-501", url="https://example.com/link1", company="Co", user_id="test-user"))
    sa_session.commit()
    co_id = _seed_company(sa_session, name="LinkedCo")
    resp = client.post("/api/jobs/job-501/link-company", json={"company_id": co_id})
    assert resp.status_code == 200
    assert resp.json() == {"status": "linked"}
    job = sa_session.query(JobModel).filter(JobModel.id == "job-501").first()
    assert job.company_id == co_id


def test_link_job_to_company_without_company_id(client, sa_session):
    sa_session.add(JobModel(id="job-502", url="https://example.com/link2", company="Co", user_id="test-user"))
    sa_session.commit()
    resp = client.post("/api/jobs/job-502/link-company", json={"company_id": None})
    assert resp.status_code == 200
    assert resp.json() == {"status": "linked"}


def test_reprocess_company_found(client, sa_session):
    co_id = _seed_company(sa_session, name="ReproCo")
    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync"),
    ):
        resp = client.post(f"/api/companies/{co_id}/reprocess")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert "execution_id" in data
    enqueue.assert_called_once_with(data["execution_id"])


def test_reprocess_company_not_found(client, sa_session):
    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync"),
    ):
        resp = client.post("/api/companies/999999999/reprocess")
    assert resp.status_code == 200
    assert resp.json() == {"error": "Not found"}
    enqueue.assert_not_called()


def test_reprocess_company_replaces_failed_execution(client, sa_session):
    from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel

    co_id = _seed_company(sa_session, name="RetryCo")
    failed = ProcessingExecutionModel(
        id="exec-failed-company",
        execution_type="company_processing",
        status="failed",
        target_type="company",
        target_id=co_id,
    )
    sa_session.add(failed)
    sa_session.commit()

    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync"),
    ):
        resp = client.post(f"/api/companies/{co_id}/reprocess")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["execution_id"] != failed.id
    enqueue.assert_called_once_with(data["execution_id"])

    sa_session.expire_all()
    old = sa_session.get(ProcessingExecutionModel, failed.id)
    assert old.status == "cancelled"


def test_reprocess_company_is_conflict_when_active(client, sa_session):
    from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel

    co_id = _seed_company(sa_session, name="ActiveCo")
    sa_session.add(
        ProcessingExecutionModel(
            id="exec-active-company",
            execution_type="company_processing",
            status="queued",
            target_type="company",
            target_id=co_id,
        )
    )
    sa_session.commit()

    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync") as publish,
    ):
        resp = client.post(f"/api/companies/{co_id}/reprocess")
    assert resp.status_code == 409
    enqueue.assert_not_called()
    publish.assert_not_called()


# ── company intake ──────────────────────────────────────────────


def test_create_company_queue_default(client, sa_session):
    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync"),
    ):
        resp = client.post(
            "/api/companies",
            json={
                "name": "Acme GmbH",
                "notes": [{"type": "text", "content": "Berlin product company"}],
                "links": [{"url": "https://acme.example", "title": "Website"}],
            },
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme GmbH"
    assert data["status"] == "queued"
    assert "execution_id" in data
    enqueue.assert_called_once_with(data["execution_id"])

    from companies.infrastructure.models.company_model import CompanyModel
    company = sa_session.query(CompanyModel).filter(CompanyModel.id == data["id"]).first()
    assert company is not None

    from companies.infrastructure.models.company_model import CompanyLinkModel

    link_rows = (
        sa_session.query(CompanyLinkModel).filter(CompanyLinkModel.company_id == data["id"]).all()
    )
    titles = [r.title for r in link_rows]
    assert any(t.startswith("note:") and "Berlin product company" in t for t in titles)
    assert any(r.url == "https://acme.example" for r in link_rows)


def test_create_company_without_queue(client, sa_session):
    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync"),
    ):
        resp = client.post(
            "/api/companies",
            json={"name": "IdleCo", "notes": [], "links": [], "queue": False},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "IdleCo"
    assert data["status"] == "created"
    assert "execution_id" not in data
    enqueue.assert_not_called()


def test_create_company_empty_body(client, sa_session):
    with (
        patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue,
        patch("shared.infrastructure.events.processing_events.publish_sync"),
    ):
        resp = client.post("/api/companies", json={})
    assert resp.status_code == 201
    assert resp.json()["status"] == "queued"
    enqueue.assert_called_once()


# ── legacy cities removal ──────────────────────────────────────


def test_dashboard_legacy_cities_endpoint_removed(client):
    """The legacy shared.cities dashboard endpoint is gone (replaced by /api/cities/list)."""
    resp = client.get("/api/cities")
    assert resp.status_code == 404
