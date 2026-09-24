"""Tests for the Companies V2 list API (GET /api/companies/list)."""

import json
import uuid

from companies.application.services.company_service import CompanyService
from companies.infrastructure.models.company_model import CompanyModel, CompanyIntelligenceModel
from companies.infrastructure.repositories.sa_company_intelligence_repository import SQLAlchemyCompanyIntelligenceRepository
from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
from jobs.infrastructure.models.job_model import JobModel
from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel
from processing.application.services.company_analysis_scoring import build_company_analysis_result
from processing.domain.enums import ExecutionType, ExecutionStatus


def _create_company(sa_session, **kwargs) -> CompanyModel:
    defaults = dict(
        name="Tech Corp",
        industry="Technology",
        city="Berlin",
        country="Germany",
        company_size="500",
        status="completed",
        workflow_log="[]",
        source="web",
        input_type="url",
        user_id="test-user",
    )
    defaults.update(kwargs)
    model = CompanyModel(**defaults)
    sa_session.add(model)
    sa_session.commit()
    sa_session.refresh(model)
    return model


def _create_intel(sa_session, company_id: str, scores: dict) -> CompanyIntelligenceModel:
    model = CompanyIntelligenceModel(
        company_id=company_id,
        scores=json.dumps(scores),
        overview=json.dumps({"products": "X"}),
    )
    sa_session.add(model)
    sa_session.commit()
    return model


class TestCompanyPinnedV2API:
    def test_list_item_carries_pinned_default_false(self, client, sa_session):
        _create_company(sa_session, name="Tech Corp")

        resp = client.get("/api/companies/list")
        data = resp.json()
        assert data["items"][0]["pinned"] is False

    def test_filter_by_pinned(self, client, sa_session):
        _create_company(sa_session, name="Pinned Corp", pinned=1)
        _create_company(sa_session, name="Plain Corp")

        resp = client.get("/api/companies/list?pinned=true")
        data = resp.json()
        assert [i["name"] for i in data["items"]] == ["Pinned Corp"]

        resp = client.get("/api/companies/list?pinned=false")
        data = resp.json()
        assert [i["name"] for i in data["items"]] == ["Plain Corp"]

        resp = client.get("/api/companies/list")
        data = resp.json()
        assert len(data["items"]) == 2

    def test_set_pinned_persists_and_toggles(self, client, sa_session):
        company = _create_company(sa_session, name="Tech Corp")

        resp = client.put(f"/api/companies/{company.id}/pinned", json={"pinned": True})
        assert resp.status_code == 200
        assert resp.json() == {"id": company.id, "pinned": True}

        data = client.get("/api/companies/list").json()
        assert data["items"][0]["pinned"] is True
        assert [i["name"] for i in client.get("/api/companies/list?pinned=true").json()["items"]] == ["Tech Corp"]

        resp = client.put(f"/api/companies/{company.id}/pinned", json={"pinned": False})
        assert resp.status_code == 200
        data = client.get("/api/companies/list").json()
        assert data["items"][0]["pinned"] is False

    def test_get_detail_carries_pinned(self, client, sa_session):
        company = _create_company(sa_session, name="Tech Corp")

        assert client.get(f"/api/companies/{company.id}").json()["pinned"] is False

        client.put(f"/api/companies/{company.id}/pinned", json={"pinned": True})
        assert client.get(f"/api/companies/{company.id}").json()["pinned"] is True

    def test_set_pinned_missing_company_returns_404(self, client, sa_session):
        resp = client.put("/api/companies/does-not-exist/pinned", json={"pinned": True})
        assert resp.status_code == 404


class TestCompanyListV2API:
    def test_list_empty(self, client):
        resp = client.get("/api/companies/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total_items"] == 0
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    def test_list_with_companies(self, client, sa_session):
        _create_company(sa_session, name="Alpha Corp", industry="Technology")
        _create_company(sa_session, name="Beta Inc", industry="Finance")

        data = client.get("/api/companies/list").json()
        assert len(data["items"]) == 2
        assert data["total_items"] == 2

    def test_list_excludes_unnamed(self, client, sa_session):
        _create_company(sa_session, name="")
        _create_company(sa_session, name=None)
        _create_company(sa_session, name="Named Co")

        data = client.get("/api/companies/list").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "Named Co"

    def test_pagination_cursor(self, client, sa_session):
        for i in range(5):
            _create_company(sa_session, name=f"Co {i}")

        data = client.get("/api/companies/list?page_size=2").json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"]

        data2 = client.get(f"/api/companies/list?page_size=2&cursor={data['next_cursor']}").json()
        assert len(data2["items"]) == 2
        assert data2["has_more"] is True

        data3 = client.get(f"/api/companies/list?page_size=2&cursor={data2['next_cursor']}").json()
        assert len(data3["items"]) == 1
        assert data3["has_more"] is False
        assert data3["next_cursor"] is None

    def test_pagination_total_constant(self, client, sa_session):
        for i in range(4):
            _create_company(sa_session, name=f"Co {i}")
        data = client.get("/api/companies/list?page_size=2").json()
        data2 = client.get(f"/api/companies/list?page_size=2&cursor={data['next_cursor']}").json()
        assert data["total_items"] == 4
        assert data2["total_items"] == 4

    def test_search_by_name_and_city(self, client, sa_session):
        _create_company(sa_session, name="SAP SE", city="Waldorf")
        _create_company(sa_session, name="Delivery Hero", city="Berlin", description="food delivery")

        data = client.get("/api/companies/list?query=berlin").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "Delivery Hero"

        data = client.get("/api/companies/list?query=delivery").json()
        assert data["total_items"] == 1

    def test_industry_filter(self, client, sa_session):
        _create_company(sa_session, name="A", industry="Technology")
        _create_company(sa_session, name="B", industry="Finance")

        data = client.get("/api/companies/list?industry=Finance").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "B"

    def test_status_filter(self, client, sa_session):
        done = _create_company(sa_session, name="Done Co")
        failed = _create_company(sa_session, name="Failed Co")
        running = _create_company(sa_session, name="Running Co")
        _create_company(sa_session, name="NoExec Co")
        for company, status in (
            (done, ExecutionStatus.COMPLETED.value),
            (failed, ExecutionStatus.FAILED.value),
            (running, ExecutionStatus.RUNNING.value),
        ):
            sa_session.add(ProcessingExecutionModel(
                id=str(uuid.uuid4()),
                execution_type=ExecutionType.COMPANY_PROCESSING.value,
                target_type="company",
                target_id=company.id,
                status=status,
            ))
        sa_session.commit()

        data = client.get("/api/companies/list?status=completed").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "Done Co"

        data = client.get("/api/companies/list?status=missing").json()
        assert data["total_items"] == 0

        data = client.get("/api/companies/list?status=none").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "NoExec Co"

        data = client.get("/api/companies/list").json()
        assert data["total_items"] == 4

    def test_sort_by_fit_score_nulls_last(self, client, sa_session):
        c1 = _create_company(sa_session, name="No Score")
        _create_intel(sa_session, c1.id, {"fit": None})
        c2 = _create_company(sa_session, name="Low Fit")
        _create_intel(sa_session, c2.id, {"fit": 30})
        c3 = _create_company(sa_session, name="High Fit")
        _create_intel(sa_session, c3.id, {"fit": 90})

        data = client.get("/api/companies/list?sort=fit_score&order=desc").json()
        names = [i["name"] for i in data["items"]]
        assert names == ["High Fit", "Low Fit", "No Score"]

        data = client.get("/api/companies/list?sort=fit_score&order=asc").json()
        names = [i["name"] for i in data["items"]]
        assert names == ["Low Fit", "High Fit", "No Score"]

    def test_sort_overall_tiebroken_by_success_then_fit(self, client, sa_session):
        c1 = _create_company(sa_session, name="A")
        _create_intel(sa_session, c1.id, {"overall": 80, "success": 70, "fit": 60})
        c2 = _create_company(sa_session, name="B")
        _create_intel(sa_session, c2.id, {"overall": 80, "success": 70, "fit": 90})
        c3 = _create_company(sa_session, name="C")
        _create_intel(sa_session, c3.id, {"overall": 80, "success": 90, "fit": 10})

        data = client.get("/api/companies/list?sort=overall_score&order=desc").json()
        assert [i["name"] for i in data["items"]] == ["C", "B", "A"]

    def test_sort_fit_tiebroken_by_overall_then_success(self, client, sa_session):
        c1 = _create_company(sa_session, name="A")
        _create_intel(sa_session, c1.id, {"fit": 70, "overall": 60, "success": 50})
        c2 = _create_company(sa_session, name="B")
        _create_intel(sa_session, c2.id, {"fit": 70, "overall": 80, "success": 20})
        c3 = _create_company(sa_session, name="C")
        _create_intel(sa_session, c3.id, {"fit": 70, "overall": 80, "success": 90})

        data = client.get("/api/companies/list?sort=fit_score&order=desc").json()
        assert [i["name"] for i in data["items"]] == ["C", "B", "A"]

    def test_sort_success_tiebroken_by_overall_then_fit(self, client, sa_session):
        c1 = _create_company(sa_session, name="A")
        _create_intel(sa_session, c1.id, {"success": 70, "overall": 60, "fit": 50})
        c2 = _create_company(sa_session, name="B")
        _create_intel(sa_session, c2.id, {"success": 70, "overall": 80, "fit": 20})
        c3 = _create_company(sa_session, name="C")
        _create_intel(sa_session, c3.id, {"success": 70, "overall": 80, "fit": 90})

        data = client.get("/api/companies/list?sort=success_score&order=desc").json()
        assert [i["name"] for i in data["items"]] == ["C", "B", "A"]

    def test_default_sort_newest_first(self, client, sa_session):
        _create_company(sa_session, name="Old Co", created_at="2026-01-01T00:00:00Z")
        _create_company(sa_session, name="New Co", created_at="2026-07-01T00:00:00Z")

        data = client.get("/api/companies/list").json()
        names = [i["name"] for i in data["items"]]
        assert names == ["New Co", "Old Co"]

    def test_sort_by_job_count_desc(self, client, sa_session):
        c1 = _create_company(sa_session, name="Few Jobs")
        c2 = _create_company(sa_session, name="Many Jobs")
        c3 = _create_company(sa_session, name="No Jobs")
        for _ in range(3):
            sa_session.add(JobModel(id=str(uuid.uuid4()), company_id=c2.id, title="SWE", status="imported", deleted=0, user_id="test-user"))
        sa_session.add(JobModel(id=str(uuid.uuid4()), company_id=c1.id, title="SWE", status="imported", deleted=0, user_id="test-user"))
        sa_session.commit()

        data = client.get("/api/companies/list?sort=job_count&order=desc").json()
        names = [i["name"] for i in data["items"]]
        assert names.index("Many Jobs") < names.index("Few Jobs")
        assert names.index("Few Jobs") < names.index("No Jobs")

    def test_sort_by_job_count_asc(self, client, sa_session):
        c1 = _create_company(sa_session, name="Few Jobs")
        c2 = _create_company(sa_session, name="Many Jobs")
        for _ in range(3):
            sa_session.add(JobModel(id=str(uuid.uuid4()), company_id=c2.id, title="SWE", status="imported", deleted=0, user_id="test-user"))
        sa_session.add(JobModel(id=str(uuid.uuid4()), company_id=c1.id, title="SWE", status="imported", deleted=0, user_id="test-user"))
        sa_session.commit()

        data = client.get("/api/companies/list?sort=job_count&order=asc").json()
        names = [i["name"] for i in data["items"]]
        assert names.index("Few Jobs") < names.index("Many Jobs")

    def test_scores_and_processing_shape(self, client, sa_session):
        c = _create_company(
            sa_session,
            name="Shape Co",
            status="processing",
            current_node="analyze_company",
            progress_pct=40,
        )
        sa_session.add(ProcessingExecutionModel(
            id=str(uuid.uuid4()),
            execution_type=ExecutionType.COMPANY_PROCESSING.value,
            target_type="company",
            target_id=c.id,
            status=ExecutionStatus.RUNNING.value,
        ))
        sa_session.commit()
        _create_intel(sa_session, c.id, {
            "overall": 78,
            "fit": 80,
            "success": 76,
            "overall_grade": "A",
        })

        item = client.get("/api/companies/list").json()["items"][0]
        assert item["scores"]["overall"] == 78
        assert item["scores"]["fit"] == 80
        assert item["scores"]["success"] == 76
        assert item["scores"]["overall_grade"] == "A"
        assert item["processing"]["status"] == "running"
        assert item["processing"]["current_node"] == "analyze_company"
        assert item["processing"]["progress_pct"] == 40

    def test_legacy_detail_route_still_works(self, client, sa_session):
        c = _create_company(sa_session, name="Detail Co")
        resp = client.get(f"/api/companies/{c.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail Co"

    def test_list_attaches_latest_processing_execution(self, client, sa_session):
        c = _create_company(sa_session, name="Exec Co")
        sa_session.add(ProcessingExecutionModel(
            id=str(uuid.uuid4()),
            execution_type=ExecutionType.COMPANY_PROCESSING.value,
            target_type="company",
            target_id=c.id,
            status=ExecutionStatus.RUNNING.value,
        ))
        sa_session.commit()

        item = client.get("/api/companies/list").json()["items"][0]
        assert item["latest_processing_execution"] is not None
        assert item["latest_processing_execution"]["status"] == "running"
        assert item["processing"]["status"] == "running"

    def test_list_uses_latest_execution_status(self, client, sa_session):
        """A stale row status must never win over the latest execution status."""
        c = _create_company(sa_session, name="Stale Co", status="queued")
        for status in (ExecutionStatus.FAILED.value, ExecutionStatus.COMPLETED.value):
            sa_session.add(ProcessingExecutionModel(
                id=str(uuid.uuid4()),
                execution_type=ExecutionType.COMPANY_PROCESSING.value,
                target_type="company",
                target_id=c.id,
                status=status,
            ))
        sa_session.commit()

        item = client.get("/api/companies/list").json()["items"][0]
        assert item["processing"]["status"] == "completed"
        assert item["latest_processing_execution"]["status"] == "completed"

    def test_list_company_without_execution(self, client, sa_session):
        _create_company(sa_session, name="NoExec Co")
        item = client.get("/api/companies/list").json()["items"][0]
        assert item["latest_processing_execution"] is None
        assert item["processing"]["status"] is None

    def test_detail_status_from_latest_execution(self, client, sa_session):
        c = _create_company(sa_session, name="Detail Exec Co", status="queued")
        sa_session.add(ProcessingExecutionModel(
            id=str(uuid.uuid4()),
            execution_type=ExecutionType.COMPANY_PROCESSING.value,
            target_type="company",
            target_id=c.id,
            status=ExecutionStatus.FAILED.value,
        ))
        sa_session.commit()

        detail = client.get(f"/api/companies/{c.id}").json()
        assert detail["status"] == "failed"


class TestCompanyHardDelete:
    def test_delete_company_hard_deletes_related_rows(self, client, sa_session):
        c = _create_company(sa_session, name="Del Co")
        _create_intel(sa_session, c.id, {"overall": 50})
        from companies.infrastructure.models.company_model import CompanyLinkModel
        sa_session.add(CompanyLinkModel(company_id=c.id, url="https://del.example"))
        sa_session.add(ProcessingExecutionModel(
            id=str(uuid.uuid4()),
            execution_type=ExecutionType.COMPANY_PROCESSING.value,
            target_type="company",
            target_id=c.id,
            status=ExecutionStatus.FAILED.value,
        ))
        sa_session.commit()
        company_id = c.id

        resp = client.delete(f"/api/companies/{company_id}")
        assert resp.status_code == 204

        assert sa_session.query(CompanyModel).filter(CompanyModel.id == company_id).first() is None
        assert sa_session.query(CompanyIntelligenceModel).filter(
            CompanyIntelligenceModel.company_id == company_id
        ).first() is None
        assert sa_session.query(CompanyLinkModel).filter(
            CompanyLinkModel.company_id == company_id
        ).first() is None
        assert sa_session.query(ProcessingExecutionModel).filter(
            ProcessingExecutionModel.target_type == "company",
            ProcessingExecutionModel.target_id == company_id,
        ).first() is None

    def test_delete_company_not_found(self, client):
        resp = client.delete("/api/companies/does-not-exist")
        assert resp.status_code == 404


class TestCompanyRelationsAPI:
    def _create(self, sa_session, name, parent=None, **kw) -> CompanyModel:
        model = _create_company(sa_session, name=name, **kw)
        if parent:
            model.parent_company_id = parent
            sa_session.commit()
            sa_session.refresh(model)
        return model

    def test_list_exposes_relation_fields(self, client, sa_session):
        main = self._create(sa_session, "Acme GmbH")
        alias = self._create(sa_session, "Acme Inc", parent=main.id)

        data = client.get("/api/companies/list").json()
        items = {i["name"]: i for i in data["items"]}
        assert items["Acme Inc"]["is_alias"] is True
        assert items["Acme Inc"]["parent_company_id"] == main.id
        assert items["Acme Inc"]["main_company"] == {"id": main.id, "name": "Acme GmbH"}
        assert items["Acme GmbH"]["alias_count"] == 1
        assert items["Acme GmbH"]["is_alias"] is False
        assert items["Acme GmbH"]["main_company"] is None

    def test_detail_exposes_relation_fields(self, client, sa_session):
        main = self._create(sa_session, "Acme GmbH")
        alias = self._create(sa_session, "Acme Inc", parent=main.id)

        detail = client.get(f"/api/companies/{alias.id}").json()
        assert detail["is_alias"] is True
        assert detail["parent_company_id"] == main.id
        assert detail["main_company"] == {"id": main.id, "name": "Acme GmbH"}
        assert detail["alias_count"] == 0

        main_detail = client.get(f"/api/companies/{main.id}").json()
        assert main_detail["is_alias"] is False
        assert main_detail["alias_count"] == 1

    def test_relate_sets_main_and_repoints_jobs(self, client, sa_session):
        main = self._create(sa_session, "Acme GmbH")
        alias = self._create(sa_session, "Acme Inc")
        job = JobModel(company_id=alias.id, deleted=0, user_id="test-user")
        sa_session.add(job)
        sa_session.commit()
        job_id = job.id

        resp = client.put(f"/api/companies/{alias.id}/main", json={"main_company_id": main.id})
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_alias"] is True
        assert body["main_company"]["id"] == main.id

        job_reloaded = sa_session.query(JobModel).filter(JobModel.id == job_id).first()
        assert job_reloaded.company_id == main.id

    def test_relate_repoints_descendant_alias_jobs(self, client, sa_session):
        main = self._create(sa_session, "Acme GmbH")
        middle = self._create(sa_session, "Acme Europe")
        leaf = self._create(sa_session, "Acme Berlin", parent=middle.id)
        job = JobModel(company_id=leaf.id, deleted=0, user_id="test-user")
        sa_session.add(job)
        sa_session.commit()

        resp = client.put(f"/api/companies/{middle.id}/main", json={"main_company_id": main.id})
        assert resp.status_code == 200
        job_reloaded = sa_session.query(JobModel).filter(JobModel.id == job.id).first()
        assert job_reloaded.company_id == main.id

    def test_unrelate_clears_main(self, client, sa_session):
        main = self._create(sa_session, "Acme GmbH")
        alias = self._create(sa_session, "Acme Inc", parent=main.id)

        resp = client.put(f"/api/companies/{alias.id}/main", json={"main_company_id": None})
        assert resp.status_code == 200
        assert resp.json()["is_alias"] is False

    def test_relate_self_link_conflict(self, client, sa_session):
        company = self._create(sa_session, "Acme GmbH")
        resp = client.put(f"/api/companies/{company.id}/main", json={"main_company_id": company.id})
        assert resp.status_code == 409

    def test_relate_to_alias_conflict(self, client, sa_session):
        main = self._create(sa_session, "Acme GmbH")
        alias = self._create(sa_session, "Acme Inc", parent=main.id)
        other = self._create(sa_session, "Other Co")

        resp = client.put(f"/api/companies/{other.id}/main", json={"main_company_id": alias.id})
        assert resp.status_code == 409

    def test_relate_missing_target_404(self, client, sa_session):
        company = self._create(sa_session, "Acme GmbH")
        resp = client.put(f"/api/companies/{company.id}/main", json={"main_company_id": "ghost"})
        assert resp.status_code == 404


class TestCompanyScoresFromProcessing:
    """The list row scores and detail scores must be exactly what company
    processing computed (build_company_analysis_result → persist_analysis)."""

    @staticmethod
    def _processed_scores() -> dict:
        return build_company_analysis_result({
            "extraction": {"name": "Acme GmbH", "industry": "Software"},
            "intelligence": {"overview": {"description": "Dev tools"}},
            "recommendation": {"priority": "A", "action": "Apply"},
            "scores": {
                "fit": 88,
                "success": 72,
                "fit_explanation": "Strong Python alignment.",
                "success_explanation": "English-first Berlin team.",
            },
        })["scores"]

    def test_list_row_scores_reflect_processing(self, client, sa_session):
        company = _create_company(sa_session, name="Acme GmbH", status="processed")
        scores = self._processed_scores()

        CompanyService(
            SQLAlchemyCompanyRepository(sa_session, user_id="test-user"),
            SQLAlchemyCompanyIntelligenceRepository(sa_session),
        ).persist_analysis(
            company.id,
            extraction={"name": "Acme GmbH", "industry": "Software"},
            intelligence={"overview": {"description": "Dev tools"}},
            recommendation={"priority": "A", "action": "Apply"},
            scores=scores,
        )

        item = client.get("/api/companies/list").json()["items"][0]
        assert item["name"] == "Acme GmbH"
        assert item["scores"]["fit"] == 88
        assert item["scores"]["success"] == 72
        assert item["scores"]["overall"] == 80
        assert item["scores"]["overall_grade"] == "A+"

    def test_detail_scores_match_intelligence_and_processing(self, client, sa_session):
        company = _create_company(sa_session, name="Acme GmbH", status="processed")
        scores = self._processed_scores()

        CompanyService(
            SQLAlchemyCompanyRepository(sa_session, user_id="test-user"),
            SQLAlchemyCompanyIntelligenceRepository(sa_session),
        ).persist_analysis(
            company.id,
            extraction={"name": "Acme GmbH"},
            intelligence={"overview": {"description": "Dev tools"}},
            recommendation={"priority": "A"},
            scores=scores,
        )

        detail = client.get(f"/api/companies/{company.id}").json()
        assert detail["scores"]["fit"] == 88
        assert detail["scores"]["success"] == 72
        assert detail["scores"]["overall"] == 80
        assert detail["scores"]["overall_grade"] == "A+"

        intel_scores = detail["intelligence"]["scores"]
        assert intel_scores["fit"] == 88
        assert intel_scores["success"] == 72
        assert intel_scores["overall"] == 80
        assert intel_scores["overall_grade"] == "A+"
        assert "company_fit_score" not in intel_scores
        assert "company_success_score" not in intel_scores
        assert "company_overall_score" not in intel_scores

    def test_company_without_processing_has_null_scores(self, client, sa_session):
        _create_company(sa_session, name="Unprocessed Co", status="created")
        item = client.get("/api/companies/list").json()["items"][0]
        assert item["scores"]["overall"] is None
        assert item["scores"]["fit"] is None
        assert item["scores"]["success"] is None
        assert item["scores"]["overall_grade"] is None
        assert item["processing"]["status"] is None


class TestCompanyTypePersist:
    """persist_analysis stores a fixed-vocabulary company_type (invalid →
    UNKNOWN, missing → None)."""

    @staticmethod
    def _persist(client, sa_session, company_id: str, extraction_company_type) -> None:
        CompanyService(
            SQLAlchemyCompanyRepository(sa_session, user_id="test-user"),
            SQLAlchemyCompanyIntelligenceRepository(sa_session),
        ).persist_analysis(
            company_id,
            extraction={"name": "Acme", "company_type": extraction_company_type},
            intelligence={},
            recommendation={},
            scores={},
        )

    def test_persist_normalizes_invalid_to_unknown(self, client, sa_session):
        c = _create_company(sa_session, name="Acme", status="queued")
        self._persist(client, sa_session, c.id, "recruiting")
        item = client.get(f"/api/companies/{c.id}").json()
        assert item["company_type"] == "UNKNOWN"

    def test_persist_keeps_valid_type(self, client, sa_session):
        c = _create_company(sa_session, name="Acme", status="queued")
        self._persist(client, sa_session, c.id, "STAFFING_COMPANY")
        item = client.get(f"/api/companies/{c.id}").json()
        assert item["company_type"] == "STAFFING_COMPANY"

    def test_persist_missing_type_is_none(self, client, sa_session):
        c = _create_company(sa_session, name="Acme", status="queued")
        self._persist(client, sa_session, c.id, None)
        item = client.get(f"/api/companies/{c.id}").json()
        assert item["company_type"] is None


class TestCompanyRecruiterForAPI:
    def test_detail_exposes_recruiter_for_and_count(self, client, sa_session):
        from jobs.infrastructure.models.job_model import JobModel
        from jobs.infrastructure.models.job_company_model import JobCompanyModel

        recruiter = _create_company(sa_session, name="RecruitCo")
        hiring_a = _create_company(sa_session, name="Acme GmbH")
        hiring_b = _create_company(sa_session, name="Beta GmbH")

        job1 = JobModel(company_id=hiring_a.id, title="Senior Backend Engineer", location="Berlin", deleted=0, workflow_log="[]", rescoring=0, user_id="test-user")
        job2 = JobModel(company_id=hiring_a.id, title="Platform Engineer", location="Munich", deleted=0, workflow_log="[]", rescoring=0, user_id="test-user")
        job3 = JobModel(company_id=hiring_b.id, title="Data Engineer", location="Berlin", deleted=0, workflow_log="[]", rescoring=0, user_id="test-user")
        sa_session.add_all([job1, job2, job3])
        sa_session.commit()
        sa_session.add_all([
            JobCompanyModel(job_id=job1.id, company_id=recruiter.id, role="recruiter"),
            JobCompanyModel(job_id=job2.id, company_id=recruiter.id, role="recruiter"),
            JobCompanyModel(job_id=job3.id, company_id=recruiter.id, role="recruiter"),
            JobCompanyModel(job_id=job1.id, company_id=hiring_a.id, role="hiring"),
            JobCompanyModel(job_id=job2.id, company_id=hiring_a.id, role="hiring"),
            JobCompanyModel(job_id=job3.id, company_id=hiring_b.id, role="hiring"),
        ])
        sa_session.commit()

        detail = client.get(f"/api/companies/{recruiter.id}").json()
        assert detail["recruiter_job_count"] == 3
        by_id = {r["company_id"]: r for r in detail["recruiter_for"]}
        assert by_id[hiring_a.id]["name"] == "Acme GmbH"
        assert by_id[hiring_a.id]["job_count"] == 2
        assert by_id[hiring_a.id]["jobs"] == [
            {"id": job2.id, "title": "Platform Engineer", "location": "Munich"},
            {"id": job1.id, "title": "Senior Backend Engineer", "location": "Berlin"},
        ]
        assert by_id[hiring_b.id]["name"] == "Beta GmbH"
        assert by_id[hiring_b.id]["job_count"] == 1
        assert by_id[hiring_b.id]["jobs"] == [
            {"id": job3.id, "title": "Data Engineer", "location": "Berlin"},
        ]

        by_role = {j["role"]: j for j in detail["recruiter_jobs"]}
        assert set(by_role) == {
            "Data Engineer",
            "Platform Engineer",
            "Senior Backend Engineer",
        }
        assert by_role["Senior Backend Engineer"]["id"] == job1.id
        assert by_role["Senior Backend Engineer"]["location"] == "Berlin"
        assert by_role["Data Engineer"]["id"] == job3.id

    def test_non_recruiter_company_has_empty_recruiter_for(self, client, sa_session):
        company = _create_company(sa_session, name="Product Co")
        detail = client.get(f"/api/companies/{company.id}").json()
        assert detail["recruiter_job_count"] == 0
        assert detail["recruiter_for"] == []

    def test_detail_lists_recruiter_jobs_without_known_hiring_company(self, client, sa_session):
        from jobs.infrastructure.models.job_model import JobModel
        from jobs.infrastructure.models.job_company_model import JobCompanyModel

        recruiter = _create_company(sa_session, name="A2G Consulting BV", company_type="STAFFING_COMPANY")
        job = JobModel(title="Senior Python Software Engineer", company_id=None, deleted=0, workflow_log="[]", rescoring=0, user_id="test-user")
        sa_session.add(job)
        sa_session.commit()
        sa_session.add_all([
            JobCompanyModel(job_id=job.id, company_id=recruiter.id, role="recruiter", company_type="staffing", confidence=0.95),
        ])
        sa_session.commit()

        detail = client.get(f"/api/companies/{recruiter.id}").json()
        assert detail["recruiter_job_count"] == 1
        assert detail["recruiter_jobs"] == [{
            "id": job.id,
            "role": "Senior Python Software Engineer",
            "location": None,
            "match": None,
            "score": None,
            "fit_score": None,
            "success_score": None,
            "overall_score": None,
            "rank": 1,
        }]
        assert detail["recruiter_for"] == []

    def test_same_company_as_hiring_and_recruiter_excluded_from_itself(self, client, sa_session):
        from jobs.infrastructure.models.job_model import JobModel
        from jobs.infrastructure.models.job_company_model import JobCompanyModel

        company = _create_company(sa_session, name="Mixed Co")
        job = JobModel(company_id=company.id, deleted=0, workflow_log="[]", rescoring=0, user_id="test-user")
        sa_session.add(job)
        sa_session.commit()
        sa_session.add_all([
            JobCompanyModel(job_id=job.id, company_id=company.id, role="recruiter"),
            JobCompanyModel(job_id=job.id, company_id=company.id, role="hiring"),
        ])
        sa_session.commit()

        detail = client.get(f"/api/companies/{company.id}").json()
        assert detail["recruiter_job_count"] == 0
        assert detail["recruiter_for"] == []

    def test_list_exposes_recruiter_job_count(self, client, sa_session):
        from jobs.infrastructure.models.job_model import JobModel
        from jobs.infrastructure.models.job_company_model import JobCompanyModel

        recruiter = _create_company(sa_session, name="RecruitCo", company_type="RECRUITING_AGENCY")
        hiring = _create_company(sa_session, name="Acme GmbH")
        product = _create_company(sa_session, name="Product Co", company_type="PRODUCT_COMPANY")
        job1 = JobModel(company_id=hiring.id, deleted=0, workflow_log="[]", rescoring=0, user_id="test-user")
        job2 = JobModel(company_id=hiring.id, deleted=0, workflow_log="[]", rescoring=0, user_id="test-user")
        job3 = JobModel(company_id=product.id, deleted=0, workflow_log="[]", rescoring=0, user_id="test-user")
        sa_session.add_all([job1, job2, job3])
        sa_session.commit()
        sa_session.add_all([
            JobCompanyModel(job_id=job1.id, company_id=recruiter.id, role="recruiter"),
            JobCompanyModel(job_id=job2.id, company_id=recruiter.id, role="recruiter"),
            JobCompanyModel(job_id=job1.id, company_id=hiring.id, role="hiring"),
            JobCompanyModel(job_id=job2.id, company_id=hiring.id, role="hiring"),
        ])
        sa_session.commit()

        items = {i["name"]: i for i in client.get("/api/companies/list").json()["items"]}
        assert items["RecruitCo"]["recruiter_job_count"] == 2
        assert items["RecruitCo"]["job_count"] == 0
        assert items["Acme GmbH"]["job_count"] == 2
        assert items["Acme GmbH"]["recruiter_job_count"] == 0
        assert items["Product Co"]["job_count"] == 1
        assert items["Product Co"]["recruiter_job_count"] == 0

    def test_list_filters_by_company_type(self, client, sa_session):
        _create_company(sa_session, name="Product Co", company_type="PRODUCT_COMPANY")
        _create_company(sa_session, name="RecruitCo", company_type="RECRUITING_AGENCY")
        _create_company(sa_session, name="StaffCo", company_type="STAFFING_COMPANY")

        product = client.get("/api/companies/list", params={"company_type": "PRODUCT_COMPANY"}).json()
        assert [i["name"] for i in product["items"]] == ["Product Co"]

        recruiting = client.get("/api/companies/list", params={"company_type": "RECRUITING_AGENCY"}).json()
        assert [i["name"] for i in recruiting["items"]] == ["RecruitCo"]

        staffing = client.get("/api/companies/list", params={"company_type": "STAFFING_COMPANY"}).json()
        assert [i["name"] for i in staffing["items"]] == ["StaffCo"]

        empty = client.get("/api/companies/list", params={"company_type": "CONSULTING_COMPANY"}).json()
        assert empty["items"] == []


class TestCompanyCreateAPI:
    def test_create_company_queues_by_default(self, client, sa_session):
        from unittest.mock import patch

        with patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue, patch(
            "shared.infrastructure.events.processing_events.publish_sync"
        ):
            resp = client.post(
                "/api/companies",
                json={
                    "name": "Acme GmbH",
                    "notes": [{"content": "Berlin product company"}],
                    "links": [{"url": "https://acme.example", "title": "Website"}],
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Acme GmbH"
        assert data["status"] == "queued"
        assert data["execution_id"]
        enqueue.assert_called_once_with(data["execution_id"])

        company = sa_session.query(CompanyModel).filter(CompanyModel.id == data["id"]).first()
        assert company is not None

        from companies.infrastructure.models.company_model import CompanyLinkModel

        link_rows = (
            sa_session.query(CompanyLinkModel)
            .filter(CompanyLinkModel.company_id == data["id"])
            .all()
        )
        titles = [r.title for r in link_rows]
        assert any(t.startswith("note:") and "Berlin product company" in t for t in titles)
        assert any(r.url == "https://acme.example" for r in link_rows)

    def test_create_company_without_queue(self, client, sa_session):
        from unittest.mock import patch

        with patch("shared.infrastructure.taskiq.client.enqueue_execution_sync") as enqueue, patch(
            "shared.infrastructure.events.processing_events.publish_sync"
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


class TestCompanyUpdateAPI:
    def test_update_company_returns_detail(self, client, sa_session):
        c = _create_company(sa_session, name="Old Name", industry="Old")
        resp = client.put(
            f"/api/companies/{c.id}",
            json={"name": "New Name", "industry": "New", "city": "Munich"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "New Name"
        assert body["industry"] == "New"
        assert body["city"] == "Munich"

        sa_session.expire_all()
        row = sa_session.get(CompanyModel, c.id)
        assert row.name == "New Name"
        assert row.industry == "New"

    def test_update_company_nulls_clear_field(self, client, sa_session):
        c = _create_company(sa_session, name="Clear Co", website="https://old.example")
        resp = client.put(f"/api/companies/{c.id}", json={"website": None})
        assert resp.status_code == 200
        sa_session.expire_all()
        row = sa_session.get(CompanyModel, c.id)
        assert row.website is None

    def test_update_company_not_found(self, client):
        resp = client.put("/api/companies/does-not-exist", json={"name": "X"})
        assert resp.status_code == 404

    def test_update_company_type_normalizes_valid_and_invalid(self, client, sa_session):
        c = _create_company(sa_session, name="Type Co", company_type="UNKNOWN")

        resp = client.put(f"/api/companies/{c.id}", json={"company_type": "STAFFING_COMPANY"})
        assert resp.status_code == 200
        assert resp.json()["company_type"] == "STAFFING_COMPANY"

        resp = client.put(f"/api/companies/{c.id}", json={"company_type": "staffing_company"})
        assert resp.json()["company_type"] == "STAFFING_COMPANY"

        resp = client.put(f"/api/companies/{c.id}", json={"company_type": "bogus type"})
        assert resp.json()["company_type"] == "UNKNOWN"

        sa_session.expire_all()
        assert sa_session.get(CompanyModel, c.id).company_type == "UNKNOWN"

    def test_update_company_type_empty_clears_to_none(self, client, sa_session):
        c = _create_company(sa_session, name="Clear Type", company_type="PRODUCT_COMPANY")
        resp = client.put(f"/api/companies/{c.id}", json={"company_type": ""})
        assert resp.status_code == 200
        assert resp.json()["company_type"] is None
        sa_session.expire_all()
        assert sa_session.get(CompanyModel, c.id).company_type is None


class TestCompanyNotesAPI:
    def test_add_list_and_get_notes(self, client, sa_session):
        c = _create_company(sa_session, name="Notes Co")
        resp = client.post(f"/api/companies/{c.id}/notes", json={"content": "First note"})
        assert resp.status_code == 201
        assert resp.json()["content"] == "First note"

        notes = client.get(f"/api/companies/{c.id}/notes").json()
        assert len(notes) == 1
        assert notes[0]["content"] == "First note"

    def test_update_and_delete_note(self, client, sa_session):
        c = _create_company(sa_session, name="Edit Notes Co")
        note = client.post(f"/api/companies/{c.id}/notes", json={"content": "Before"}).json()

        resp = client.put(f"/api/companies/{c.id}/notes/{note['id']}", json={"content": "After"})
        assert resp.status_code == 200
        assert resp.json()["content"] == "After"

        notes = client.get(f"/api/companies/{c.id}/notes").json()
        assert notes[0]["content"] == "After"

        resp = client.delete(f"/api/companies/{c.id}/notes/{note['id']}")
        assert resp.status_code == 200
        assert client.get(f"/api/companies/{c.id}/notes").json() == []

    def test_update_missing_note_404(self, client, sa_session):
        c = _create_company(sa_session, name="No Notes Co")
        resp = client.put(f"/api/companies/{c.id}/notes/999999", json={"content": "X"})
        assert resp.status_code == 404


class TestCompanyLinksAPI:
    def test_add_list_and_update_link(self, client, sa_session):
        c = _create_company(sa_session, name="Links Co")
        resp = client.post(
            f"/api/companies/{c.id}/links",
            json={"url": "https://acme.example", "title": "Website", "description": "Main site"},
        )
        assert resp.status_code == 201
        link = resp.json()
        assert link["url"] == "https://acme.example"
        assert link["title"] == "Website"

        updated = client.put(
            f"/api/companies/{c.id}/links/{link['id']}",
            json={"url": "https://new.example", "title": "Careers", "description": ""},
        ).json()
        assert updated["url"] == "https://new.example"
        assert updated["title"] == "Careers"

        links = client.get(f"/api/companies/{c.id}").json()["links"]
        assert len(links) == 1
        assert links[0]["url"] == "https://new.example"

    def test_delete_link(self, client, sa_session):
        c = _create_company(sa_session, name="Del Link Co")
        link = client.post(f"/api/companies/{c.id}/links", json={"url": "https://x.example"}).json()
        resp = client.delete(f"/api/companies/{c.id}/links/{link['id']}")
        assert resp.status_code == 200
        detail = client.get(f"/api/companies/{c.id}").json()
        assert detail["links"] == []
        assert detail["notes"] == []

    def test_update_missing_link_404(self, client, sa_session):
        c = _create_company(sa_session, name="No Links Co")
        resp = client.put(f"/api/companies/{c.id}/links/999999", json={"url": "https://x.example"})
        assert resp.status_code == 404
