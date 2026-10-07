"""Tests for the Opportunities bounded context service.

Covers:
- Manual create (validation, content-hash dedupe, created event)
- Extract with explicit uncertainty (no fabricated fields)
- Entity resolution (existing job/company links, no auto-creation)
- Evaluate with deterministic overall/recommendation reuse
- Pending evaluation when information is insufficient
- Status transitions and evaluation history
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from opportunities.application.services.opportunity_service import OpportunityService
from opportunities.domain.entities.opportunity import OpportunityStatus
from opportunities.domain.events import (
    OpportunityCreated,
    OpportunityEvaluated,
    OpportunityExtracted,
    OpportunityLinked,
)
from shared.application.exceptions import NotFoundError, ValidationError


class FakeLLM:
    """Returns queued structured payloads in call order."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = 0

    def generate_structured(self, prompt, schema=None, timeout=None):
        self.calls += 1
        return SimpleNamespace(content=self._payloads.pop(0))


class FakeOpportunityRepo:
    def __init__(self):
        self._rows = {}
        self._next = 1

    def _new(self, data):
        row = dict(data)
        row["id"] = f"opp-{self._next}"
        self._next += 1
        return row

    def create(self, data):
        row = self._new(data)
        self._rows[row["id"]] = row
        return dict(row)

    def get_by_id(self, opportunity_id):
        row = self._rows.get(opportunity_id)
        return dict(row) if row else None

    def get_by_content_hash(self, content_hash):
        return next(
            (dict(r) for r in self._rows.values() if r.get("content_hash") == content_hash),
            None,
        )

    def get_by_source_message(self, source, source_message_id):
        return next(
            (
                dict(r)
                for r in self._rows.values()
                if r.get("source") == source and r.get("source_message_id") == source_message_id
            ),
            None,
        )

    def update(self, opportunity_id, data):
        row = self._rows.get(opportunity_id)
        if not row:
            return None
        row.update(data)
        return dict(row)

    def delete(self, opportunity_id):
        return self._rows.pop(opportunity_id, None) is not None


class FakeEvaluationRepo:
    def __init__(self):
        self._rows = []
        self._next = 1

    def create(self, data):
        row = dict(data)
        row["id"] = f"eval-{self._next}"
        self._next += 1
        self._rows.append(row)
        return dict(row)

    def list_for_opportunity(self, opportunity_id):
        return [dict(r) for r in self._rows if r["opportunity_id"] == opportunity_id]


class FakeJobRepo:
    def __init__(self, jobs=None):
        self._jobs = {j["id"]: j for j in (jobs or [])}

    def get_by_id(self, job_id):
        return self._jobs.get(job_id)

    def get_by_url_fragment(self, fragment):
        return next((j for j in self._jobs.values() if fragment in (j.get("url") or "")), None)


class FakeCompanyRepo:
    def __init__(self, companies=None):
        self._companies = list(companies or [])

    def get_by_id(self, company_id):
        return next((c for c in self._companies if c["id"] == company_id), None)

    def list_for_matching(self):
        return list(self._companies)


class FakeSkillRepo:
    def get_by_name(self, name):
        return None


class FakeProfileRepo:
    def __init__(self, profile=None):
        self._profile = profile

    def get_current_profile(self):
        return self._profile


class FakeRuleRepo:
    def get_enabled_by_scopes(self, scopes):
        return []


class RecordingCollector:
    def __init__(self):
        self._events = []

    def publish(self, event):
        self._events.append(event)

    @property
    def events(self):
        return list(self._events)


def _extract_payload():
    return {
        "role_title": "Senior Backend Engineer",
        "company": {"name": "Acme GmbH", "website": None, "confidence": 0.6, "state": "inferred"},
        "job_urls": ["https://www.linkedin.com/jobs/view/4333938709/"],
        "job_description_present": False,
        "recruiter": {"name": "Jane", "email": "jane@acme.example", "state": "known"},
        "location": {"value": None, "state": "unknown"},
        "skills": [{"name": "Python", "state": "known"}],
        "uncertainties": ["location"],
    }


def _evaluate_payload():
    return {
        "technical_match": 88,
        "seniority_match": "match",
        "location_match": "unknown",
        "fit": 85,
        "success": 70,
        "concerns": ["Sponsorship is unclear"],
        "missing_requirements": ["Job location"],
        "unknown_information": ["Visa sponsorship"],
        "enough_to_apply": False,
        "recommended_next_action": "Ask the recruiter for the location and JD",
    }


def _make_service(llm_payloads=None, **kwargs):
    collector = RecordingCollector()
    service = OpportunityService(
        opportunity_repo=kwargs.get("opportunity_repo") or FakeOpportunityRepo(),
        evaluation_repo=kwargs.get("evaluation_repo") or FakeEvaluationRepo(),
        job_repo=kwargs.get("job_repo") or FakeJobRepo(),
        company_repo=kwargs.get("company_repo") or FakeCompanyRepo(),
        skill_repo=kwargs.get("skill_repo") or FakeSkillRepo(),
        profile_repo=kwargs.get("profile_repo")
        if "profile_repo" in kwargs
        else FakeProfileRepo({"id": "profile-1", "name": "Hassan"}),
        rule_repo=kwargs.get("rule_repo") or FakeRuleRepo(),
        llm=FakeLLM(llm_payloads or []),
        event_publisher=collector,
    )
    return service, collector


def _create_input(**kwargs):
    data = {
        "source": "manual",
        "sender": "Jane",
        "sender_email": "jane@acme.example",
        "subject": "Senior Backend Engineer role",
        "raw_content": "Hi Hassan, we are hiring a Senior Backend Engineer. Interested?",
    }
    data.update(kwargs)
    return data


class TestCreate:
    def test_create_manual(self):
        service, collector = _make_service()
        created, duplicate = service.create_manual(_create_input())
        assert created["status"] == OpportunityStatus.NEW
        assert created["content_hash"]
        assert duplicate is False
        assert isinstance(collector.events[0], OpportunityCreated)

    def test_create_requires_raw_content(self):
        service, _ = _make_service()
        with pytest.raises(ValidationError):
            service.create_manual(_create_input(raw_content="   "))

    def test_create_rejects_unknown_source(self):
        service, _ = _make_service()
        with pytest.raises(ValidationError):
            service.create_manual(_create_input(source="carrier-pigeon"))

    def test_duplicate_content_returns_existing(self):
        service, _ = _make_service()
        first, _ = service.create_manual(_create_input())
        second, duplicate = service.create_manual(_create_input())
        assert duplicate is True
        assert second["id"] == first["id"]


class TestProcess:
    def test_process_extracts_links_and_scores(self):
        job = {"id": "job-1", "title": "Senior Backend Engineer", "url": "https://www.linkedin.com/jobs/view/4333938709/"}
        service, collector = _make_service(
            [_extract_payload(), _evaluate_payload()],
            job_repo=FakeJobRepo([job]),
        )
        created, _ = service.create_manual(_create_input())
        result = service.process(created["id"])
        assert result["status"] == OpportunityStatus.EVALUATED
        assert result["job_id"] == "job-1"
        assert result["overall_score"] == 79  # round(85*0.6 + 70*0.4)
        assert result["recommendation"] == "consider"
        assert result["evaluation_status"] == "complete"
        assert service._evaluations.list_for_opportunity(created["id"])
        kinds = {type(e) for e in collector.events}
        assert {OpportunityExtracted, OpportunityLinked, OpportunityEvaluated} <= kinds

    def test_process_does_not_create_companies_or_skills(self):
        companies = FakeCompanyRepo()
        skills = FakeSkillRepo()
        service, _ = _make_service(
            [_extract_payload(), _evaluate_payload()],
            company_repo=companies,
            skill_repo=skills,
        )
        created, _ = service.create_manual(_create_input())
        result = service.process(created["id"])
        assert result["company_id"] is None
        assert companies._companies == []
        assert skills.get_by_name("Python") is None

    def test_insufficient_information_stays_pending(self):
        thin = dict(_extract_payload())
        thin["role_title"] = None
        thin["job_urls"] = []
        service, _ = _make_service([thin])
        created, _ = service.create_manual(_create_input(raw_content="Hi!"))
        result = service.process(created["id"])
        assert result["status"] == OpportunityStatus.NEEDS_INFO
        assert result["overall_score"] is None
        assert result["evaluation_status"] == "pending"
        assert result["missing_information"]

    def test_process_missing_raises_404(self):
        service, _ = _make_service()
        with pytest.raises(NotFoundError):
            service.process("opp-missing")


class TestStatusAndLinks:
    def test_invalid_transition_rejected(self):
        service, _ = _make_service()
        created, _ = service.create_manual(_create_input())
        with pytest.raises(ValidationError):
            service.set_status(created["id"], OpportunityStatus.APPLIED)

    def test_link_unknown_job_404(self):
        service, _ = _make_service()
        created, _ = service.create_manual(_create_input())
        with pytest.raises(NotFoundError):
            service.set_links(created["id"], job_id="job-missing")
