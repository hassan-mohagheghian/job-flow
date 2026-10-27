"""Comprehensive SA repository tests."""

import sys
import os
import json
import pytest
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from shared.infrastructure.database.sqlalchemy_config import Base
import jobs.infrastructure.models.job_model
import skills.infrastructure.models.skill_model
import companies.infrastructure.models.company_model

import jobs.infrastructure.models.misc_models
import rules.infrastructure.models.rule_model


@pytest.fixture
def session(_engine):
    connection = _engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    s = Session()
    yield s
    s.close()
    transaction.rollback()
    connection.close()


# ── Job Repository ────────────────────────────────────────────────

class TestSAJobRepository:
    def _job(self, session, **kwargs):
        from jobs.infrastructure.models.job_model import JobModel
        m = JobModel(user_id="test-user", **kwargs)
        session.add(m)
        session.commit()
        return m

    def test_get_by_num(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1", company="Google")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        result = repo.get_by_id(job.id)
        assert result is not None
        assert result["id"] == job.id

    def test_get_by_num_not_found(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.get_by_id("nonexistent") is None

    def test_get_by_num_with_company(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from companies.infrastructure.models.company_model import CompanyModel
        co = CompanyModel(name="Google", user_id="test-user")
        session.add(co)
        session.commit()
        job = self._job(session, url="https://ex.com/1", company="Google", company_id=co.id)
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        result = repo.get_by_id(job.id)
        assert result["company_id"] == co.id

    def test_list_jobs(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", company="A")
        self._job(session, url="https://ex.com/2", company="B")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs()
        assert total == 2
        assert len(jobs) == 2

    def test_list_jobs_pagination(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        for i in range(5):
            self._job(session, url=f"https://ex.com/{i}", company=f"C{i}")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(offset=0, limit=2)
        assert total == 5
        assert len(jobs) == 2

    def test_list_jobs_filter_companies(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", company="Google")
        self._job(session, url="https://ex.com/2", company="Meta")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(filters={"filter_companies": "Google"})
        assert total == 1

    def test_list_jobs_filter_cities(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", location="Berlin")
        self._job(session, url="https://ex.com/2", location="Munich")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(filters={"filter_cities": "Berlin"})
        assert total == 1

    def test_list_jobs_filter_tech(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", stack="Python")
        self._job(session, url="https://ex.com/2", stack="Java")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(filters={"filter_tech": "Python"})
        assert total == 1

    def test_list_jobs_filter_work_types(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", work_types=["Remote"])
        self._job(session, url="https://ex.com/2", work_types=["On-site"])
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(filters={"filter_work_types": "Remote"})
        assert total == 1

    def test_list_jobs_filter_employment_types(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", employment_types=["Full-time"])
        self._job(session, url="https://ex.com/2", employment_types=["Part-time"])
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(filters={"filter_employment_types": "Full-time"})
        assert total == 1

    def test_list_jobs_filter_response_status(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", response_status="applied")
        self._job(session, url="https://ex.com/2", response_status="pending")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(filters={"filter_response_status": "applied"})
        assert total == 1

    def test_list_jobs_filter_applied(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", apply_time="2024-01-01")
        self._job(session, url="https://ex.com/2")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(filters={"filter_applied": "true"})
        assert total == 1

    def test_list_jobs_sorting(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", overall_score=50)
        self._job(session, url="https://ex.com/2", overall_score=90)
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(sort_by="overall_score", sort_dir="desc")
        assert jobs[0]["overall_score"] == 90

    def test_list_jobs_invalid_sort(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        jobs, total = repo.list_jobs(sort_by="invalid_field", sort_dir="invalid")
        assert len(jobs) == 1

    def test_update(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        result = repo.update_by_id(job.id, {"notes": "test", "apply_time": "2024-01-01"})
        assert result["notes"] == "test"

    def test_update_not_found(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.update_by_id("nonexistent", {"notes": "test"}) is None

    def test_update_empty(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        result = repo.update_by_id(job.id, {})
        assert result is not None

    def test_delete(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.delete_by_id(job.id) is True

    def test_mark_deleted(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        repo.mark_deleted(job.id)
        result = repo.get_by_id(job.id)
        assert result["deleted"] == 1

    def test_mark_rescoring(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        repo.mark_rescoring(job.id, False)
        result = repo.get_by_id(job.id)
        assert result["rescoring"] == 0

    def test_get_all_active(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1")
        self._job(session, url="https://ex.com/2", deleted=1)
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        active = repo.get_all_active()
        assert len(active) == 1

    def test_get_by_url(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        result = repo.get_by_url("https://ex.com/1")
        assert result["id"] == job.id

    def test_get_by_url_not_found(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.get_by_url("https://nonexistent.com") is None

    def test_get_num_by_url(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.get_id_by_url("https://ex.com/1") == job.id

    def test_get_num_by_url_not_found(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.get_id_by_url("https://nonexistent.com") is None

    def test_upsert_insert(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        result = repo.upsert({"url": "https://ex.com/1", "company": "A"})
        assert result["company"] == "A"

    def test_upsert_update(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1", company="A")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        result = repo.upsert({"id": job.id, "company": "B"})
        assert result["company"] == "B"

    def test_update_fields(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.update_fields(job.id, company_id=5) is True

    def test_update_workflow_log(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.update_workflow_log(job.id, "[\"step1\"]") is True

    def test_set_deleted_by_url(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job1 = self._job(session, url="https://ex.com/1")
        job2 = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        count = repo.set_deleted_by_url("https://ex.com/1", exclude_id=job1.id)
        assert count == 1

    def test_delete_all_active(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1")
        self._job(session, url="https://ex.com/2")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        count = repo.delete_all_active()
        assert count == 2

    def test_get_company_id(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1", company_id="00000000-0000-0000-0000-000000000005")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.get_company_id(job.id) == "00000000-0000-0000-0000-000000000005"

    def test_get_company_id_none(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.get_company_id(job.id) is None

    def test_get_dashboard_counts(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", overall_score=90)
        self._job(session, url="https://ex.com/2", overall_score=40)
        self._job(session, url="https://ex.com/3", overall_score=80)
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        counts = repo.get_dashboard_counts()
        assert counts["jobs_total"] == 3
        assert counts["jobs_high_match"] == 2

    def test_get_location_data(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", location="Berlin")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        result = repo.get_location_data()
        assert len(result) == 1
        assert result[0]["location"] == "Berlin"

    def test_get_company_id_by_num(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        job = self._job(session, url="https://ex.com/1", company_id="00000000-0000-0000-0000-000000000003")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        assert repo.get_company_id_by_id(job.id) == "00000000-0000-0000-0000-000000000003"

    def test_get_jobs_by_company_id(self, session):
        from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
        from jobs.infrastructure.models.job_model import JobModel
        self._job(session, url="https://ex.com/1", company_id="00000000-0000-0000-0000-000000000001")
        self._job(session, url="https://ex.com/2", company_id="00000000-0000-0000-0000-000000000002")
        repo = SQLAlchemyJobRepository(session, user_id="test-user")
        result = repo.get_jobs_by_company_id("00000000-0000-0000-0000-000000000001")
        assert len(result) == 1


# ── Skill Repository ──────────────────────────────────────────────

class TestSASkillRepository:
    def test_list_visible(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", level=8, hidden=0, user_id="test-user"))
        session.add(SkillModel(name="Java", level=5, hidden=1, user_id="test-user"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.list_visible()
        assert len(result) == 1

    def test_list_visible_by_category(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", level=8, category="technical", user_id="test-user"))
        session.add(SkillModel(name="Leadership", level=5, category="professional", user_id="test-user"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.list_visible(category="technical")
        assert len(result) == 1

    def test_list_hidden(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="OldSkill", hidden=1, user_id="test-user"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.list_hidden()
        assert len(result) == 1

    def test_get_by_id(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", level=8, user_id="test-user"))
        session.commit()
        skill_id = session.query(SkillModel).first().id
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.get_by_id(skill_id)
        assert result["name"] == "Python"

    def test_get_by_id_not_found(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.get_by_id(999) is None

    def test_get_by_name(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", level=8, user_id="test-user"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.get_by_name("Python")
        assert result["name"] == "Python"

    def test_get_by_name_not_found(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.get_by_name("Nonexistent") is None

    def test_create(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.create({"name": "Rust", "level": 5, "category": "technical"})
        assert result["name"] == "Rust"

    def test_update(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", level=8, user_id="test-user"))
        session.commit()
        skill_id = session.query(SkillModel).first().id
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.update(skill_id, {"level": 10, "tags": ["web"]})
        assert result["level"] == 10

    def test_update_not_found(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.update(999, {"level": 10}) is None

    def test_delete(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", user_id="test-user"))
        session.commit()
        skill_id = session.query(SkillModel).first().id
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.delete(skill_id) is True

    def test_delete_not_found(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.delete(999) is False

    def test_set_hidden(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", user_id="test-user"))
        session.commit()
        skill_id = session.query(SkillModel).first().id
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.set_hidden(skill_id, 1)
        assert result["hidden"] == 1

    def test_set_hidden_not_found(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.set_hidden(999, 1) is None

    def test_rename(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", user_id="test-user"))
        session.commit()
        skill_id = session.query(SkillModel).first().id
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.rename(skill_id, "Python3")
        assert result["name"] == "Python3"

    def test_rename_same_name(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", user_id="test-user"))
        session.commit()
        skill_id = session.query(SkillModel).first().id
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.rename(skill_id, "Python")
        assert result["name"] == "Python"

    def test_rename_conflict(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", user_id="test-user"))
        session.add(SkillModel(name="Java", user_id="test-user"))
        session.commit()
        java_id = session.query(SkillModel).filter(SkillModel.name == "Java").first().id
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.rename(java_id, "Python")
        assert result is None

    def test_rename_not_found(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.rename(999, "New") is None

    def test_merge(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", user_id="test-user"))
        session.add(SkillModel(name="Python3", user_id="test-user"))
        session.commit()
        target = session.query(SkillModel).filter(SkillModel.name == "Python").first()
        source = session.query(SkillModel).filter(SkillModel.name == "Python3").first()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.merge(target.id, [source.id])
        assert result["status"] == "merged"
        assert "Python3" in result["aliases"]

    def test_merge_target_not_found(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.merge(999, [])
        assert "error" in result

    def test_get_categories(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", level=8, category="technical", user_id="test-user"))
        session.add(SkillModel(name="Java", level=5, category="technical", user_id="test-user"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        cats = repo.get_categories()
        assert len(cats) == 1
        assert cats[0]["count"] == 2

    def test_get_stats(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", level=8, source="user", market_relevance=9.0, user_id="test-user"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        stats = repo.get_stats()
        assert stats["total"] == 1
        assert stats["hidden"] == 0

    def test_bulk_hide(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", user_id="test-user"))
        session.add(SkillModel(name="Java", user_id="test-user"))
        session.commit()
        ids = [s.id for s in session.query(SkillModel).all()]
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        count = repo.bulk_hide(ids)
        assert count == 2

    def test_bulk_categorize(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", user_id="test-user"))
        session.commit()
        ids = [s.id for s in session.query(SkillModel).all()]
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        count = repo.bulk_categorize(ids, "technical")
        assert count == 1

    def test_get_relationships(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillRelationshipModel
        session.add(SkillRelationshipModel(skill_name="Python", related_name="Django", relation_type="related"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.get_relationships("Python")
        assert len(result) == 1

    def test_create_relationship(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.create_relationship({"skill_name": "Python", "related_name": "Django", "relation_type": "related"})
        assert result is True

    def test_delete_relationship(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillRelationshipModel
        session.add(SkillRelationshipModel(skill_name="A", related_name="B", relation_type="related"))
        session.commit()
        rel_id = session.query(SkillRelationshipModel).first().id
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.delete_relationship(rel_id) is True

    def test_get_all(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", user_id="test-user"))
        session.add(SkillModel(name="Java", user_id="test-user"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.get_all()
        assert len(result) == 2

    def test_get_level_by_name(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", level=8, user_id="test-user"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.get_level_by_name("Python") == 8

    def test_get_level_by_name_not_found(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.get_level_by_name("Nonexistent") is None

    def test_update_fields_by_name(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        from skills.infrastructure.models.skill_model import SkillModel
        session.add(SkillModel(name="Python", level=8, user_id="test-user"))
        session.commit()
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.update_fields_by_name("Python", level=10) is True

    def test_update_fields_by_name_not_found(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        assert repo.update_fields_by_name("Nonexistent", level=10) is False

    def test_create_from_dict(self, session):
        from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
        repo = SQLAlchemySkillRepository(session, user_id="test-user")
        result = repo.create_from_dict({"name": "Go", "level": 6, "source": "service"})
        assert result["name"] == "Go"


# ── Company Repository ────────────────────────────────────────────

class TestSACompanyRepository:
    def test_list_all(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        from companies.infrastructure.models.company_model import CompanyModel
        session.add(CompanyModel(name="Google", user_id="test-user"))
        session.add(CompanyModel(name="Meta", user_id="test-user"))
        session.commit()
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        result = repo.list_all()
        assert len(result) == 2

    def test_get_by_id(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        from companies.infrastructure.models.company_model import CompanyModel
        co = CompanyModel(name="Google", user_id="test-user")
        session.add(co)
        session.commit()
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        result = repo.get_by_id(co.id)
        assert result["name"] == "Google"

    def test_get_by_id_not_found(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        assert repo.get_by_id("00000000-0000-0000-0000-000000000000") is None

    def test_create(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        result = repo.create({"name": "Google", "industry": "Tech"})
        assert result["name"] == "Google"

    def test_update(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        from companies.infrastructure.models.company_model import CompanyModel
        co = CompanyModel(name="Google", user_id="test-user")
        session.add(co)
        session.commit()
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        result = repo.update(co.id, {"industry": "Tech", "tech_stack": ["Python"]})
        assert result["industry"] == "Tech"

    def test_update_not_found(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        assert repo.update("00000000-0000-0000-0000-000000000000", {"name": "X"}) is None

    def test_delete(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        from companies.infrastructure.models.company_model import CompanyModel
        co = CompanyModel(name="Google", user_id="test-user")
        session.add(co)
        session.commit()
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        assert repo.delete(co.id) is True

    def test_get_intelligence(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        from companies.infrastructure.models.company_model import CompanyModel, CompanyIntelligenceModel
        co = CompanyModel(name="Google", user_id="test-user")
        session.add(co)
        session.commit()
        session.add(CompanyIntelligenceModel(company_id=co.id, overview="Great"))
        session.commit()
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        result = repo.get_intelligence(co.id)
        assert result["overview"] == "Great"

    def test_get_intelligence_not_found(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        assert repo.get_intelligence("00000000-0000-0000-0000-000000000000") is None

    def test_insert(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        result = repo.insert({"name": "TestCo"})
        assert result["name"] == "TestCo"

    def test_get_total_count(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        from companies.infrastructure.models.company_model import CompanyModel
        session.add(CompanyModel(name="A", user_id="test-user"))
        session.add(CompanyModel(name="B", user_id="test-user"))
        session.commit()
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        assert repo.get_total_count() == 2

    def test_get_all_with_job_counts(self, session):
        from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
        from companies.infrastructure.models.company_model import CompanyModel
        from jobs.infrastructure.models.job_model import JobModel
        co = CompanyModel(name="Google", user_id="test-user")
        session.add(co)
        session.commit()
        session.add(JobModel(url="https://ex.com/1", company_id=co.id, user_id="test-user"))
        session.commit()
        repo = SQLAlchemyCompanyRepository(session, user_id="test-user")
        result = repo.get_all_with_job_counts()
        assert result[0]["job_count"] == 1
