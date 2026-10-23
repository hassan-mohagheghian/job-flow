"""Tests for the Job Analysis workflow.

Covers:
- Pure scoring helpers (normalization, overall, recommendation, grade, payload)
- Prompt and output schema builders
- User profile/resume/rules text builders
- Analysis nodes (LoadContext, PrepareProfile, Analyze, ExtractSkills, Score,
  Recommend, Summarize, Persist)
- The JobAnalysisGraph end-to-end (mocked LLM)
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from processing.application.services.job_analysis_inputs import (
    build_candidate_profile_text,
    build_profile_documents_text,
    build_profile_text,
    build_resume_text,
    build_scoring_rules_text,
)
from processing.application.services.job_analysis_prompt import (
    JOB_ANALYSIS_PROMPT_VERSION,
    JOB_ANALYSIS_SCHEMA_VERSION,
    build_job_analysis_output_schema,
    build_job_analysis_prompt,
)
from processing.application.services.job_analysis_validation import JobAnalysisOutput
from processing.application.services import job_analysis_scoring as scoring
from processing.application.workflows import progress_ops
from processing.application.workflows.job_analysis import JobAnalysisGraph
from processing.application.workflows.job_analysis.nodes import (
    AnalysisReadyNode,
    AnalyzeNode,
    ExecutionFailedNode,
    ExtractSkillsNode,
    LoadContextNode,
    PersistNode,
    PersistSkillsNode,
    PrepareProfileNode,
    RecommendNode,
    ScoreNode,
    SummarizeNode,
)
from processing.domain.enums import ExecutionStatus
from processing.domain.workflow.job_processing_state import JobProcessingState


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


def _job_dict(**overrides) -> dict:
    data = {
        "id": "job-uuid-1",
        "url": "https://example.com/job",
        "company": "Acme Inc",
        "role": "Senior Backend Engineer",
        "title": "Senior Backend Engineer",
        "location": "Berlin, Germany",
        "notes": "[]",
        "links": "[]",
        "raw_description": "We need a senior backend engineer with Python, Postgres and Kafka.",
        "description": "We need a senior backend engineer with Python, Postgres and Kafka.",
    }
    data.update(overrides)
    return data


class FakeJobService:
    def __init__(self, job=None, error=None):
        self._job = job
        self._error = error

    def get_job(self, job_id):
        if self._error is not None:
            raise self._error
        return self._job


class FakeLLM:
    def __init__(self, content=None, error=None):
        self._content = content
        self._error = error
        self.calls = []

    def generate_structured(self, prompt, schema=None, timeout=None):
        self.calls.append({"prompt": prompt, "schema": schema, "timeout": timeout})
        if self._error is not None:
            raise self._error
        return type("Resp", (), {"content": self._content})


class FakeSkillRepo:
    def __init__(self, skills=None, error=None):
        self._skills = skills or []
        self._error = error
        self.mentions = []
        self._next_id = 1000

    def list_visible(self):
        if self._error is not None:
            raise self._error
        return self._skills

    def resolve_skill(self, data):
        if self._error is not None:
            raise self._error
        for skill in self._skills:
            if skill["name"] == data["name"]:
                return skill.get("id") or 1
        self._next_id += 1
        self._skills.append({"name": data["name"], **data})
        return self._next_id

    def upsert_mentions(self, skill_id, source_type, source_id, status="", evidence="[]"):
        self.mentions.append({"skill_id": skill_id, "source_type": source_type, "source_id": source_id, "status": status})

    def delete_mentions_for_source(self, source_type, source_id):
        self.mentions = [m for m in self.mentions if not (m["source_type"] == source_type and m["source_id"] == source_id)]


class FakeResumeRepo:
    """Fake candidate source repository exposing get_latest_by_type.

    Built from ``original``/``linkedin`` raw text strings to keep the
    TestPrepareProfileNode assertions readable.
    """

    def __init__(self, original=None, linkedin=None, error=None):
        self._original = original
        self._linkedin = linkedin
        self._error = error

    def get_latest_by_type(self, profile_id, source_type):
        if self._error is not None:
            raise self._error
        if source_type == "resume":
            raw = self._original
        elif source_type == "linkedin":
            raw = self._linkedin
        else:
            return None
        if not raw:
            return None
        return {"source_type": source_type, "version": 1, "raw_text": raw, "status": "processed"}


class FakeRuleRepo:
    def __init__(self, rules=None, error=None):
        self._rules = rules or []
        self._error = error

    def get_enabled_by_scopes(self, scopes):
        if self._error is not None:
            raise self._error
        return self._rules


class FakeCandidateProfileRepo:
    def __init__(self, profile=None, error=None):
        self._profile = profile
        self._error = error

    def get_current_profile(self):
        if self._error is not None:
            raise self._error
        return self._profile

    def get_or_create_current(self):
        if self._error is not None:
            raise self._error
        return self._profile or {"id": "profile-1", "skills": []}


def _candidate_profile(**overrides) -> dict:
    profile = {
        "id": "profile-1",
        "candidate_id": "cand-1",
        "version": 2,
        "name": "Jane Doe",
        "title": "Senior Backend Engineer",
        "headline": "Distributed systems at scale",
        "summary": "8+ years building backend platforms.",
        "location": "Berlin, Germany",
        "skills": [
            {
                "name": "Python",
                "level": 4,
                "category": "Language",
                "confidence": 0.96,
                "origin": "explicit",
                "years_of_experience": 6,
                "last_used": "2026-01",
                "evidence": {"sources": ["resume"]},
            }
        ],
        "experiences": [
            {
                "company": "Acme Inc",
                "role": "Senior Backend Engineer",
                "start_date": "2021-03",
                "end_date": "present",
                "summary": "Led event-driven platform.",
            }
        ],
        "projects": [{"name": "Job Search AI", "description": "AI career platform.", "url": "https://example.com"}],
        "educations": [{"institution": "TU Berlin", "degree": "MSc CS", "field": "Computer Science"}],
        "certificates": [{"name": "AWS Solutions Architect", "issuer": "Amazon"}],
        "interests": [{"name": "Kubernetes"}],
        "languages": [{"name": "English", "proficiency": "fluent"}],
    }
    profile.update(overrides)
    return profile


class FakeJobRepo:
    def __init__(self):
        self.updated = None

    def update_fields(self, job_id, **fields):
        self.updated = {"job_id": job_id, **fields}
        return True


class FakeSummaryRepo:
    def __init__(self):
        self.upserted = None

    def upsert(self, data):
        self.upserted = data
        return data


class FakeAnalysisRepo:
    def __init__(self):
        self.upserted = None

    def upsert_by_job_id(self, job_id, data):
        self.upserted = {"job_id": job_id, **data}
        return self.upserted


class RecordingEventPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event_name, execution_id, job_id, status, **kwargs):
        self.events.append((event_name, execution_id, job_id, status, kwargs))


def _state(job_id="job-uuid-1", execution_id="exec-1") -> JobProcessingState:
    state = JobProcessingState(execution_id=execution_id, job_id=job_id)
    state.workflow_progress = progress_ops.build_initial_progress(execution_id)
    return state


def _payload(**overrides) -> dict:
    payload = {
        "title": "Senior Backend Engineer",
        "company": "Acme Inc",
        "role": "Senior Backend Engineer",
        "location": "Berlin, Germany",
        "salary": "90k",
        "stack": "Python, Postgres",
        "visa": "sponsored",
        "employment_types": ["full-time"],
        "work_types": ["hybrid"],
        "industry": "fintech",
        "domain": "payments",
        "description": "Long description here.",
        "scores": {"fit": 85, "success": 70},
        "scores_explanation": {
            "fit_factors": ["Python backend experience"],
            "success_factors": ["Senior level", "Berlin"],
            "concerns": ["No Kafka experience"],
        },
        "recommendation": "skip",
        "apply_reason": "Great role overall.",
        "summary": {
            "summary": "Backend role at Acme.",
            "resume_fit": "Strong fit.",
            "note": "Apply early.",
        },
        "skills": [
            {"name": "Python", "category": "Language", "level": 4, "status": "matched", "evidence": "posted"},
            {"name": "Kafka", "category": "Data", "level": 1, "status": "missing", "evidence": "posted"},
        ],
        "insights": ["Mention Kafka coursework", "Ask about salary band"],
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------- #
# Scoring helpers
# --------------------------------------------------------------------------- #


class TestNormalizeScore100:
    def test_none_and_empty(self):
        assert scoring.normalize_score_100(None) is None
        assert scoring.normalize_score_100("") is None

    def test_string_and_float(self):
        assert scoring.normalize_score_100("85") == 85
        assert scoring.normalize_score_100(75.6) == 75

    def test_clamps(self):
        assert scoring.normalize_score_100(120) == 100
        assert scoring.normalize_score_100(-5) == 0

    def test_unparseable(self):
        assert scoring.normalize_score_100("abc") is None
        assert scoring.normalize_score_100([]) is None


class TestCalculateOverallScore:
    def test_weighted_round(self):
        assert scoring.calculate_overall_score(80, 70) == round(80 * 0.6 + 70 * 0.4)
        assert scoring.calculate_overall_score(100, 0) == 60

    def test_missing_component(self):
        assert scoring.calculate_overall_score(None, 70) is None
        assert scoring.calculate_overall_score(80, None) is None


class TestRecommendationForOverall:
    def test_buckets(self):
        assert scoring.recommendation_for_overall(90) == "apply"
        assert scoring.recommendation_for_overall(80) == "apply"
        assert scoring.recommendation_for_overall(75) == "consider"
        assert scoring.recommendation_for_overall(60) == "consider"
        assert scoring.recommendation_for_overall(50) == "skip"

    def test_none(self):
        assert scoring.recommendation_for_overall(None) == "skip"


class TestCoerceRecommendation:
    def test_valid(self):
        assert scoring.coerce_recommendation("APPLY") == "apply"
        assert scoring.coerce_recommendation(" consider ") == "consider"

    def test_invalid(self):
        assert scoring.coerce_recommendation("maybe") == "skip"
        assert scoring.coerce_recommendation(None) == "skip"


class TestGradeForOverall:
    def test_buckets(self):
        assert scoring.grade_for_overall(95) == "A++"
        assert scoring.grade_for_overall(85) == "A+"
        assert scoring.grade_for_overall(72) == "A"
        assert scoring.grade_for_overall(60) == "B"
        assert scoring.grade_for_overall(40) == "C"
        assert scoring.grade_for_overall(10) == "D"
        assert scoring.grade_for_overall(None) == "P"


class TestNormalizePayload:
    def test_json_string(self):
        assert scoring.normalize_payload('{"scores": {"fit": 1}}') == {"scores": {"fit": 1}}

    def test_bad_string(self):
        assert scoring.normalize_payload("not json") == {}

    def test_dict(self):
        assert scoring.normalize_payload({"a": 1}) == {"a": 1}

    def test_other(self):
        assert scoring.normalize_payload(None) == {}
        assert scoring.normalize_payload([1, 2]) == {}


class TestBuildAnalysisResult:
    def test_computes_deterministic_scores_and_recommendation(self):
        result = scoring.build_analysis_result(_payload())

        assert result["scores"] == {"fit": 85, "success": 70, "overall": 79}
        assert result["recommendation"] == "consider"
        assert result["apply_reason"] == "Great role overall."
        assert result["summary"]["summary"] == "Backend role at Acme."
        assert result["scores_explanation"]["concerns"] == ["No Kafka experience"]
        assert result["insights"] == ["Mention Kafka coursework", "Ask about salary band"]

    def test_clamps_llm_scores(self):
        payload = _payload(scores={"fit": 150, "success": -10})
        result = scoring.build_analysis_result(payload)
        assert result["scores"] == {"fit": 100, "success": 0, "overall": 60}

    def test_missing_scores(self):
        result = scoring.build_analysis_result({"scores": None})
        assert result["scores"] == {"fit": None, "success": None, "overall": None}
        assert result["recommendation"] == "skip"


class TestNormalizeSkills:
    def test_filters_and_defaults(self):
        skills = scoring.normalize_skills(
            [
                {"name": "Python", "status": "MATCHED"},
                {"name": "Kafka"},
                {"name": ""},
                "not-a-dict",
                None,
            ]
        )
        assert len(skills) == 2
        assert skills[0]["status"] == "matched"
        assert skills[0]["level"] is None
        assert skills[1]["status"] == "missing"

    def test_non_list(self):
        assert scoring.normalize_skills("nope") == []


class TestCoerceStatus:
    def test_valid(self):
        assert scoring.coerce_status("matched") == "matched"
        assert scoring.coerce_status("LOW") == "low"

    def test_invalid(self):
        assert scoring.coerce_status("nope") == "missing"
        assert scoring.coerce_status(None) == "missing"


# --------------------------------------------------------------------------- #
# Prompt + inputs
# --------------------------------------------------------------------------- #


class TestJobAnalysisPrompt:
    def test_schema_structure(self):
        schema = build_job_analysis_output_schema()
        assert schema["type"] == "object"
        required = set(schema["required"])
        assert {"scores", "recommendation", "apply_reason", "summary", "skills", "insights"} <= required
        assert schema["properties"]["skills"]["items"]["required"] == ["name"]
        assert set(schema["properties"]["scores"]["required"]) == {"fit", "success"}

    def test_prompt_contains_all_sections(self):
        prompt = build_job_analysis_prompt("job text", "profile text", "rules text", "resume text", "documents text")
        assert "job text" in prompt
        assert "profile text" in prompt
        assert "rules text" in prompt
        assert "documents text" in prompt
        assert "Respond ONLY with valid JSON" in prompt

    def test_prompt_falls_back_to_resume_text_when_no_documents(self):
        prompt = build_job_analysis_prompt("job text", "profile text", "rules text", "resume text")
        assert "resume text" in prompt

    def test_prompt_forbids_schema_wrapper(self):
        prompt = build_job_analysis_prompt("job text", "profile text", "rules text", "resume text")
        assert "Return the data object itself" in prompt
        assert 'never include "type", "properties" or "required"' in prompt

    def test_prompt_is_work_arrangement_agnostic(self):
        prompt = build_job_analysis_prompt("job text", "profile text", "rules text", "resume text")
        assert "professional evaluating a role" in prompt
        assert "visa-sponsored" not in prompt
        assert "salary/visa" not in prompt

    def test_versions(self):
        assert JOB_ANALYSIS_PROMPT_VERSION == "1.6.2"
        assert JOB_ANALYSIS_SCHEMA_VERSION == "1.1.0"


class TestJobAnalysisInputs:
    def test_profile_text_empty(self):
        assert build_profile_text([]) == "(no skills registered)"

    def test_profile_text_with_skills(self):
        text = build_profile_text(
            [{"name": "Python", "level": 4, "category": "Language"}, {"name": "Kafka"}]
        )
        assert "Total skills: 2" in text
        assert "- Python (level 4, Language)" in text
        assert "- Kafka" in text

    def test_resume_text(self):
        assert build_resume_text(None) == "(no resume available)"
        assert build_resume_text("hello") == "hello"
        assert len(build_resume_text("x" * 10000)) == 6000

    def test_profile_documents_text_empty(self):
        assert build_profile_documents_text(None, None) == "(no resume or LinkedIn profile available)"

    def test_profile_documents_text_resume_only(self):
        text = build_profile_documents_text("Resume raw", None)
        assert "RESUME TEXT (latest):" in text
        assert "Resume raw" in text
        assert "LINKEDIN" not in text

    def test_profile_documents_text_both_sources(self):
        text = build_profile_documents_text("Resume raw", "LinkedIn raw")
        assert "RESUME TEXT (latest):\nResume raw" in text
        assert "LINKEDIN PROFILE TEXT (latest):\nLinkedIn raw" in text

    def test_profile_documents_text_truncates_each_source(self):
        text = build_profile_documents_text("R" * 10000, "L" * 10000)
        assert "R" * 6000 in text
        assert "R" * 6001 not in text
        assert "L" * 6000 in text
        assert "L" * 6001 not in text

    def test_scoring_rules(self):
        assert build_scoring_rules_text([]) == "(no scoring rules set)"
        text = build_scoring_rules_text(
            [{"key": "VISA_OK", "value": "must sponsor", "priority": 5}]
        )
        assert "#5" in text and "VISA_OK" in text and "weight:5" in text


class TestBuildCandidateProfileText:
    def test_empty_profile(self):
        assert build_candidate_profile_text({}) == "(no candidate profile available)"

    def test_header_and_sections(self):
        text = build_candidate_profile_text(_candidate_profile())
        assert "Jane Doe" in text
        assert "Senior Backend Engineer" in text
        assert "Distributed systems at scale" in text
        assert "8+ years building backend platforms." in text
        assert "Berlin, Germany" in text
        assert "SKILLS:" in text
        assert "EXPERIENCE:" in text
        assert "PROJECTS:" in text
        assert "EDUCATION:" in text
        assert "CERTIFICATES:" in text
        assert "INTERESTS:" in text
        assert "LANGUAGES:" in text

    def test_skill_metadata_included(self):
        text = build_candidate_profile_text(_candidate_profile())
        assert "- Python (level 4, confidence 0.96, years 6, evidence: resume)" in text

    def test_experience_fields(self):
        text = build_candidate_profile_text(_candidate_profile())
        assert "Acme Inc - Senior Backend Engineer (2021-03 -> present)" in text
        assert "Led event-driven platform." in text

    def test_truncates_to_max_chars(self):
        profile = _candidate_profile(summary="S" * 20000)
        text = build_candidate_profile_text(profile)
        assert len(text) <= 6000

    def test_missing_children_defaults(self):
        text = build_candidate_profile_text({"name": "Noah", "title": "Engineer"})
        assert "Noah" in text
        assert "SKILLS:" not in text


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


class TestJobAnalysisValidation:
    def test_valid_payload_passes(self):
        validated = JobAnalysisOutput.model_validate(_payload())
        assert validated.scores.fit == 85
        assert validated.scores.success == 70
        assert validated.recommendation == "skip"
        assert validated.skills[0].name == "Python"

    def test_required_fields_enforced(self):
        for field in ("scores", "recommendation", "apply_reason", "summary", "skills", "insights"):
            payload = _payload()
            del payload[field]
            with pytest.raises(ValidationError):
                JobAnalysisOutput.model_validate(payload)

    def test_invalid_recommendation_rejected(self):
        with pytest.raises(ValidationError):
            JobAnalysisOutput.model_validate(_payload(recommendation="maybe"))

    def test_invalid_skill_status_rejected(self):
        with pytest.raises(ValidationError):
            JobAnalysisOutput.model_validate(
                _payload(skills=[{"name": "Python", "status": "expert"}])
            )

    def test_scores_clamped(self):
        validated = JobAnalysisOutput.model_validate(_payload(scores={"fit": 150, "success": -5}))
        assert validated.scores.fit == 100
        assert validated.scores.success == 0

    def test_scores_missing_component_rejected(self):
        with pytest.raises(ValidationError):
            JobAnalysisOutput.model_validate(_payload(scores={"fit": 85}))

    def test_work_types_string_coerced(self):
        validated = JobAnalysisOutput.model_validate(_payload(work_types="hybrid, remote"))
        assert validated.work_types == ["hybrid", "remote"]

    def test_null_skills_rejected(self):
        with pytest.raises(ValidationError):
            JobAnalysisOutput.model_validate(_payload(skills=None))

    def test_skill_without_name_rejected(self):
        with pytest.raises(ValidationError):
            JobAnalysisOutput.model_validate(_payload(skills=[{"status": "matched"}]))

    def test_non_dict_payload_rejected(self):
        with pytest.raises(ValidationError):
            JobAnalysisOutput.model_validate([1, 2, 3])


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #


class TestLoadContextNode:
    def test_loads_prepared_content(self):
        node = LoadContextNode(FakeJobService(_job_dict()))
        state = node(_state())
        assert state.processing_context is not None
        assert "senior backend engineer" in state.processing_context.combined_text
        assert state.status != ExecutionStatus.FAILED

    def test_missing_job_fails(self):
        node = LoadContextNode(FakeJobService(None))
        state = node(_state())
        assert state.status == ExecutionStatus.FAILED
        assert any("not found" in e for e in state.errors)

    def test_no_prepared_content_fails(self):
        node = LoadContextNode(FakeJobService(_job_dict(raw_description=None, description=None)))
        state = node(_state())
        assert state.status == ExecutionStatus.FAILED
        assert any("no prepared content" in e for e in state.errors)

    def test_service_error_fails(self):
        node = LoadContextNode(FakeJobService(None, error=RuntimeError("db down")))
        state = node(_state())
        assert state.status == ExecutionStatus.FAILED
        assert any("db down" in e for e in state.errors)


class TestPrepareProfileNode:
    def test_gathers_profile_inputs(self):
        skills = [{"name": "Python", "level": 4, "category": "Language"}]
        rules = [{"key": "VISA_OK", "value": "must sponsor", "priority": 1}]
        node = PrepareProfileNode(
            FakeSkillRepo(skills),
            FakeResumeRepo(original="Resume text here", linkedin="LinkedIn raw here"),
            FakeRuleRepo(rules),
            candidate_profile_repo=FakeCandidateProfileRepo(None),
        )
        state = _state()
        state.processing_context = type("Ctx", (), {"combined_text": "job text"})()
        state = node(state)

        assert state.analysis_context["job_text"] == "job text"
        assert "Python" in state.analysis_context["profile_text"]
        assert "VISA_OK" in state.analysis_context["scoring_rules"]
        assert "Resume text here" in state.analysis_context["resume_text"]
        assert "RESUME TEXT (latest):" in state.analysis_context["profile_documents"]
        assert "LinkedIn raw here" in state.analysis_context["profile_documents"]

    def test_keeps_linkedin_as_separate_supplement(self):
        node = PrepareProfileNode(
            FakeSkillRepo(), FakeResumeRepo(original="Resume raw", linkedin="LinkedIn raw"), FakeRuleRepo(),
            candidate_profile_repo=FakeCandidateProfileRepo(None),
        )
        state = node(_state())
        assert state.analysis_context["resume_text"] == "Resume raw"
        assert "Resume raw" in state.analysis_context["profile_documents"]
        assert "LinkedIn raw" in state.analysis_context["profile_documents"]

    def test_linkedin_only_yields_empty_resume_text(self):
        node = PrepareProfileNode(
            FakeSkillRepo(), FakeResumeRepo(original=None, linkedin="LinkedIn raw"), FakeRuleRepo(),
            candidate_profile_repo=FakeCandidateProfileRepo(None),
        )
        state = node(_state())
        assert state.analysis_context["resume_text"] == "(no resume available)"
        assert "LinkedIn raw" in state.analysis_context["profile_documents"]

    def test_profile_failure_degrades(self):
        node = PrepareProfileNode(
            FakeSkillRepo(error=RuntimeError("boom")), FakeResumeRepo(), FakeRuleRepo(),
            candidate_profile_repo=FakeCandidateProfileRepo(None),
        )
        state = node(_state())
        assert state.analysis_context["profile_text"] == "(no skills registered)"
        assert any("boom" in e for e in state.errors)

    def test_structured_profile_takes_priority(self):
        skills = [{"name": "Python", "level": 4, "category": "Language"}]
        rules = [{"key": "VISA_OK", "value": "must sponsor", "priority": 1}]
        node = PrepareProfileNode(
            FakeSkillRepo(skills),
            FakeResumeRepo(original="Resume text here", linkedin="LinkedIn raw here"),
            FakeRuleRepo(rules),
            candidate_profile_repo=FakeCandidateProfileRepo(_candidate_profile()),
        )
        state = _state()
        state.processing_context = type("Ctx", (), {"combined_text": "job text"})()
        state = node(state)

        assert "Jane Doe" in state.analysis_context["profile_documents"]
        assert "SKILLS:" in state.analysis_context["profile_documents"]
        assert "RESUME TEXT (latest):" not in state.analysis_context["profile_documents"]
        assert "Python" in state.analysis_context["profile_text"]
        assert state.analysis_context["profile_text"].startswith("Total skills: 1")
        assert state.analysis_context["resume_text"] == "Resume text here"

    def test_structured_profile_skills_win(self):
        node = PrepareProfileNode(
            FakeSkillRepo([{"name": "CuratedSkill", "level": 5}]),
            FakeResumeRepo(),
            FakeRuleRepo(),
            candidate_profile_repo=FakeCandidateProfileRepo(_candidate_profile()),
        )
        state = node(_state())
        assert "Python" in state.analysis_context["profile_text"]
        assert "CuratedSkill" not in state.analysis_context["profile_text"]

    def test_no_profile_falls_back_to_raw_documents(self):
        node = PrepareProfileNode(
            FakeSkillRepo(),
            FakeResumeRepo(original="Resume raw", linkedin="LinkedIn raw"),
            FakeRuleRepo(),
            candidate_profile_repo=FakeCandidateProfileRepo(None),
        )
        state = node(_state())
        assert "RESUME TEXT (latest):" in state.analysis_context["profile_documents"]
        assert "LinkedIn raw" in state.analysis_context["profile_documents"]

    def test_profile_repo_failure_degrades(self):
        node = PrepareProfileNode(
            FakeSkillRepo(),
            FakeResumeRepo(original="Resume raw", linkedin="LinkedIn raw"),
            FakeRuleRepo(),
            candidate_profile_repo=FakeCandidateProfileRepo(error=RuntimeError("profile db down")),
        )
        state = node(_state())
        assert state.analysis_context["resume_text"] == "(no resume available)"
        assert any("profile db down" in e for e in state.errors)

    def test_no_profile_repo_keeps_legacy_behavior(self):
        node = PrepareProfileNode(
            FakeSkillRepo(),
            FakeResumeRepo(original="Resume raw", linkedin="LinkedIn raw"),
            FakeRuleRepo(),
            candidate_profile_repo=FakeCandidateProfileRepo(None),
        )
        state = node(_state())
        assert "RESUME TEXT (latest):" in state.analysis_context["profile_documents"]


class TestAnalyzeNode:
    def test_calls_llm_and_stores_raw_payload(self):
        llm = FakeLLM(_payload())
        state = _state()
        state.analysis_context["job_text"] = "job text"
        state = AnalyzeNode(llm)(state)

        assert len(llm.calls) == 1
        assert llm.calls[0]["timeout"] == 240
        assert state.analysis_context["raw_payload"]["scores"]["fit"] == 85
        assert state.analysis_context["raw_payload"]["prompt_version"] == "1.6.2"
        assert state.status != ExecutionStatus.FAILED

    def test_unwraps_schema_echo_payload(self):
        wrapped = {"type": "object", "properties": _payload()}
        state = _state()
        state.analysis_context["job_text"] = "job text"
        state = AnalyzeNode(FakeLLM(content=json.dumps(wrapped)))(state)

        assert state.status != ExecutionStatus.FAILED
        payload = state.analysis_context["raw_payload"]
        assert payload["title"] == "Senior Backend Engineer"
        assert payload["company"] == "Acme Inc"
        assert payload["location"] == "Berlin, Germany"

    def test_retries_when_extraction_fields_are_all_empty(self):
        degraded = _payload(
            title=None,
            company=None,
            role=None,
            location=None,
            description=None,
        )

        class DegradedThenFixedLLM(FakeLLM):
            def __init__(self):
                super().__init__(content=json.dumps(_payload()))
                self._first = True

            def generate_structured(self, prompt, schema=None, timeout=None):
                if self._first:
                    self._first = False
                    self.calls.append({"prompt": prompt, "schema": schema, "timeout": timeout})
                    return type("Resp", (), {"content": json.dumps(degraded)})
                return super().generate_structured(prompt, schema=schema, timeout=timeout)

        state = _state()
        state.analysis_context["job_text"] = "job text"
        llm = DegradedThenFixedLLM()
        state = AnalyzeNode(llm)(state)

        assert len(llm.calls) == 2
        assert state.status != ExecutionStatus.FAILED
        assert state.analysis_context["raw_payload"]["title"] == "Senior Backend Engineer"
        assert "omitted the extracted job fields" in llm.calls[1]["prompt"]
        assert "never wrap it in a JSON Schema" in llm.calls[1]["prompt"]

    def test_no_job_text_fails(self):
        llm = FakeLLM(_payload())
        state = AnalyzeNode(llm)(_state())
        assert state.status == ExecutionStatus.FAILED
        assert llm.calls == []

    def test_llm_error_fails(self):
        state = _state()
        state.analysis_context["job_text"] = "job text"
        state = AnalyzeNode(FakeLLM(error=RuntimeError("provider down")))(state)
        assert state.status == ExecutionStatus.FAILED
        assert any("provider down" in e for e in state.errors)

    def test_unparseable_content_fails(self):
        state = _state()
        state.analysis_context["job_text"] = "job text"
        with patch("processing.application.workflows.job_analysis.nodes.analyze_node._STEP_BUDGET_SECONDS", 0.1):
            state = AnalyzeNode(FakeLLM(content="not a dict"))(state)
        assert state.status == ExecutionStatus.FAILED

    def test_retries_once_on_json_parse_failure_then_succeeds(self):
        class FlakyLLM(FakeLLM):
            def __init__(self):
                super().__init__(content=_payload())
                self._fail_first = True

            def generate_structured(self, prompt, schema=None, timeout=None):
                if self._fail_first:
                    self._fail_first = False
                    self.calls.append({"prompt": prompt, "schema": schema, "timeout": timeout})
                    raise RuntimeError("Failed to parse opencode JSON output\nRaw output: {truncated")
                return super().generate_structured(prompt, schema=schema, timeout=timeout)

        state = _state()
        state.analysis_context["job_text"] = "job text"
        llm = FlakyLLM()
        state = AnalyzeNode(llm)(state)

        assert len(llm.calls) == 2
        assert state.status != ExecutionStatus.FAILED
        assert state.analysis_context["raw_payload"]["scores"]["fit"] == 85
        assert "SHORTER, COMPLETE JSON" in llm.calls[1]["prompt"]

    def test_no_retry_when_generic_error(self):
        state = _state()
        state.analysis_context["job_text"] = "job text"
        llm = FakeLLM(error=RuntimeError("provider down"))
        AnalyzeNode(llm)(state)
        assert len(llm.calls) == 1

    def test_schema_invalid_output_fails_with_clean_message(self):
        invalid = _payload()
        del invalid["skills"]
        state = _state()
        state.analysis_context["job_text"] = "job text"
        with patch("processing.application.workflows.job_analysis.nodes.analyze_node._STEP_BUDGET_SECONDS", 0.1):
            state = AnalyzeNode(FakeLLM(content=json.dumps(invalid)))(state)

        assert state.status == ExecutionStatus.FAILED
        assert "raw_payload" not in state.analysis_context
        assert any("does not match the required format" in e for e in state.errors)
        assert any("skills" in e for e in state.errors)

    def test_schema_invalid_once_then_valid_retries(self):
        class SchemaFixLLM(FakeLLM):
            def __init__(self):
                super().__init__(content=_payload())
                self._fix_next = True

            def generate_structured(self, prompt, schema=None, timeout=None):
                self.calls.append({"prompt": prompt, "schema": schema, "timeout": timeout})
                if self._fix_next:
                    self._fix_next = False
                    return type("Resp", (), {"content": json.dumps(_payload(recommendation="maybe"))})
                return type("Resp", (), {"content": json.dumps(_payload())})

        state = _state()
        state.analysis_context["job_text"] = "job text"
        llm = SchemaFixLLM()
        state = AnalyzeNode(llm)(state)

        assert len(llm.calls) == 2
        assert state.status != ExecutionStatus.FAILED
        assert state.analysis_context["raw_payload"]["scores"]["fit"] == 85
        assert "SHORTER, COMPLETE JSON" in llm.calls[1]["prompt"]

    def test_retries_format_errors_then_succeeds(self):
        class FlakyLLM(FakeLLM):
            def __init__(self):
                super().__init__(content=_payload())
                self._fail_count = 0
                self._fail_until = 3

            def generate_structured(self, prompt, schema=None, timeout=None):
                if self._fail_count < self._fail_until:
                    self._fail_count += 1
                    self.calls.append({"prompt": prompt, "schema": schema, "timeout": timeout})
                    return type("Resp", (), {"content": json.dumps({"scores": {"fit": 80}})})
                return super().generate_structured(prompt, schema=schema, timeout=timeout)

        state = _state()
        state.analysis_context["job_text"] = "job text"
        llm = FlakyLLM()
        with patch("processing.application.workflows.job_analysis.nodes.analyze_node._STEP_BUDGET_SECONDS", 30):
            state = AnalyzeNode(llm)(state)

        assert len(llm.calls) == 4
        assert state.status != ExecutionStatus.FAILED
        assert state.analysis_context["raw_payload"]["scores"]["fit"] == 85

    def test_schema_invalid_twice_fails(self):
        state = _state()
        state.analysis_context["job_text"] = "job text"
        invalid = _payload()
        invalid["recommendation"] = "maybe"
        llm = FakeLLM(content=json.dumps(invalid))
        with patch("processing.application.workflows.job_analysis.nodes.analyze_node._STEP_BUDGET_SECONDS", 0.1):
            state = AnalyzeNode(llm)(state)

        assert state.status == ExecutionStatus.FAILED
        assert any("does not match the required format" in e for e in state.errors)


class TestExtractSkillsNode:
    def test_normalizes_skills_onto_context(self):
        state = _state()
        state.analysis_context["raw_payload"] = _payload()
        state = ExtractSkillsNode()(state)

        skills = state.analysis_context["normalized_skills"]
        assert skills[0]["name"] == "Python"
        assert skills[0]["status"] == "matched"
        assert skills[1]["status"] == "missing"

    def test_missing_payload_yields_empty(self):
        state = ExtractSkillsNode()(_state())
        assert state.analysis_context["normalized_skills"] == []


class TestScoreNode:
    def test_builds_canonical_result(self):
        state = _state()
        state.analysis_context["raw_payload"] = _payload()
        state = ScoreNode()(state)

        assert state.analysis_result["scores"]["overall"] == 79
        assert state.analysis_result["recommendation"] == "consider"
        assert state.analysis_result["fields"]["company"] == "Acme Inc"

    def test_merges_normalized_skills(self):
        state = _state()
        state.analysis_context["raw_payload"] = _payload()
        state = ExtractSkillsNode()(state)
        state = ScoreNode()(state)

        assert len(state.analysis_result["skills"]) == 2
        assert state.analysis_result["skills"][0]["name"] == "Python"


class TestRecommendNode:
    def test_derives_recommendation_from_overall(self):
        state = _state()
        state.analysis_result = scoring.build_analysis_result(_payload())
        state = RecommendNode()(state)
        assert state.analysis_result["recommendation"] == "consider"
        assert state.analysis_result["apply_reason"] == "Great role overall."

    def test_apply_reason_fallback(self):
        payload = _payload(apply_reason="", recommendation="apply", scores={"fit": 95, "success": 90})
        state = _state()
        state.analysis_result = scoring.build_analysis_result(payload)
        state = RecommendNode()(state)
        assert "Overall score 93" in state.analysis_result["apply_reason"]
        assert state.analysis_result["recommendation"] == "apply"


class TestSummarizeNode:
    def test_fills_summary_fields(self):
        state = _state()
        state.analysis_result = scoring.build_analysis_result(_payload())
        state = SummarizeNode()(state)
        assert state.analysis_result["summary"]["summary"] == "Backend role at Acme."
        assert state.analysis_result["summary"]["resume_fit"] == "Strong fit."


class TestPersistNode:
    def test_persists_job_summary_and_analysis(self):
        job_repo, summary_repo, analysis_repo = FakeJobRepo(), FakeSummaryRepo(), FakeAnalysisRepo()
        node = PersistNode(job_repo, summary_repo, analysis_repo)
        state = _state()
        state.analysis_context["raw_payload"] = _payload()
        state.analysis_result = scoring.build_analysis_result(_payload())

        state = node(state)

        assert state.persisted is True
        assert job_repo.updated["fit_score"] == 85
        assert job_repo.updated["overall_score"] == 79
        assert job_repo.updated["apply_reason"] == "Great role overall."
        assert isinstance(job_repo.updated["updated_at"], datetime)
        assert summary_repo.upserted["score"] == "A"
        assert summary_repo.upserted["summary"] == "Backend role at Acme."
        assert analysis_repo.upserted["job_id"] == "job-uuid-1"
        assert analysis_repo.upserted["recommendation"] == "consider"
        assert json.loads(analysis_repo.upserted["payload"])["scores"]["overall"] == 79

    def test_missing_result_records_error(self):
        node = PersistNode(FakeJobRepo(), FakeSummaryRepo(), FakeAnalysisRepo())
        state = node(_state())
        assert state.persisted is False
        assert any("No analysis result" in e for e in state.errors)

    def test_null_fields_not_written(self):
        job_repo, summary_repo, analysis_repo = FakeJobRepo(), FakeSummaryRepo(), FakeAnalysisRepo()
        node = PersistNode(job_repo, summary_repo, analysis_repo)
        payload = _payload(
            title=None, company=None, role=None, location=None, salary=None,
            visa=None, employment_type=None, work_types=[],
        )
        state = _state()
        state.analysis_context["raw_payload"] = payload
        state.analysis_result = scoring.build_analysis_result(payload)

        state = node(state)

        assert state.persisted is True
        for key in ("title", "company", "role", "location", "salary", "visa", "employment_type", "work_types"):
            assert key not in job_repo.updated, f"{key} should not be written when null"
        assert job_repo.updated["fit_score"] == 85
        assert job_repo.updated["overall_score"] == 79
        assert job_repo.updated["apply_reason"] == "Great role overall."

    def test_empty_result_skips_job_update(self):
        class NeverCalledRepo(FakeJobRepo):
            def update_fields(self, job_id, **fields):
                raise AssertionError("update_fields should not be called")

        node = PersistNode(NeverCalledRepo(), FakeSummaryRepo(), FakeAnalysisRepo())
        payload = _payload(
            title=None, company=None, role=None, location=None, salary=None, stack=None,
            visa=None, employment_types=None, industry=None, domain=None, description=None,
            work_types=[], apply_reason="", scores=None,
        )
        state = _state()
        state.analysis_context["raw_payload"] = payload
        state.analysis_result = scoring.build_analysis_result(payload)

        state = node(state)
        assert state.persisted is True

    def test_persists_city_wiring_when_city_service_provided(self):
        class FakeCityService:
            def __init__(self):
                self.calls = []

            def normalize_and_ensure(self, raw, address=""):
                self.calls.append(raw)
                return {"id": "city-1", "city": "Berlin", "country": "Germany"}

        city_service = FakeCityService()
        job_repo, summary_repo, analysis_repo = FakeJobRepo(), FakeSummaryRepo(), FakeAnalysisRepo()
        node = PersistNode(job_repo, summary_repo, analysis_repo, city_service=city_service)
        state = _state()
        state.analysis_context["raw_payload"] = _payload()
        state.analysis_result = scoring.build_analysis_result(_payload())

        state = node(state)

        assert state.persisted is True
        assert city_service.calls == ["Berlin, Germany"]
        assert job_repo.updated["city_id"] == "city-1"
        assert job_repo.updated["city"] == "Berlin"
        assert job_repo.updated["country"] == "Germany"

    def test_persist_skips_city_wiring_when_location_missing(self):
        class FakeCityService:
            def normalize_and_ensure(self, raw, address=""):
                raise AssertionError("should not normalize without a location")

        job_repo, summary_repo, analysis_repo = FakeJobRepo(), FakeSummaryRepo(), FakeAnalysisRepo()
        node = PersistNode(job_repo, summary_repo, analysis_repo, city_service=FakeCityService())
        payload = _payload(location=None)
        state = _state()
        state.analysis_context["raw_payload"] = payload
        state.analysis_result = scoring.build_analysis_result(payload)

        state = node(state)

        assert state.persisted is True
        assert "city_id" not in job_repo.updated


class TestPersistSkillsNode:
    def test_resolves_and_links_each_skill(self):
        skill_repo = FakeSkillRepo([{"name": "Python", "level": 4}])
        node = PersistSkillsNode(skill_repo)
        state = _state()
        state.analysis_result = {
            "skills": [
                {"name": "Python", "category": "Language", "status": "matched", "evidence": "posted"},
                {"name": "Kafka", "category": "Data", "status": "missing", "evidence": "posted"},
            ]
        }

        state = node(state)

        assert state.status != ExecutionStatus.FAILED
        assert len(skill_repo.mentions) == 2
        assert all(m["source_type"] == "job" for m in skill_repo.mentions)
        assert all(m["source_id"] == "job-uuid-1" for m in skill_repo.mentions)
        statuses = {m["status"] for m in skill_repo.mentions}
        assert statuses == {"matched", "missing"}
        assert skill_repo.mentions[0]["skill_id"] == 1  # Python resolved to existing

    def test_skips_blank_names(self):
        skill_repo = FakeSkillRepo()
        node = PersistSkillsNode(skill_repo)
        state = _state()
        state.analysis_result = {"skills": [{"name": ""}, {"name": "  "}]}

        node(state)
        assert skill_repo.mentions == []

    def test_no_skills_is_noop(self):
        skill_repo = FakeSkillRepo()
        node = PersistSkillsNode(skill_repo)
        state = node(_state())
        assert state.status != ExecutionStatus.FAILED
        assert skill_repo.mentions == []

    def test_error_marks_failed(self):
        skill_repo = FakeSkillRepo(error=RuntimeError("db down"))
        node = PersistSkillsNode(skill_repo)
        state = _state()
        state.analysis_result = {"skills": [{"name": "Python"}]}
        state = node(state)
        assert state.status == ExecutionStatus.FAILED
        assert any("persist skills" in e and "db down" in e for e in state.errors)


class TestTerminalNodes:
    def test_analysis_ready(self):
        state = AnalysisReadyNode()(_state())
        assert state.status == ExecutionStatus.COMPLETED

    def test_execution_failed(self):
        state = _state()
        state.errors.append("boom")
        state = ExecutionFailedNode()(state)
        assert state.status == ExecutionStatus.FAILED


# --------------------------------------------------------------------------- #
# Graph end-to-end
# --------------------------------------------------------------------------- #


class TestJobAnalysisGraph:
    _MISSING = object()

    def _build(self, llm=None, job=_MISSING, job_service_error=None, persist_error=None):
        if job is self._MISSING:
            job = _job_dict()
        job_service = FakeJobService(job, job_service_error)

        class FailingJobRepo(FakeJobRepo):
            def update_fields(self, job_id, **fields):
                raise persist_error

        return JobAnalysisGraph(
            job_service=job_service,
            skill_repo=FakeSkillRepo([{"name": "Python", "level": 4, "category": "Language"}]),
            source_repo=FakeResumeRepo(original="My resume"),
            rule_repo=FakeRuleRepo([{"key": "VISA_OK", "value": "sponsor", "priority": 1}]),
            job_repo=FailingJobRepo() if persist_error else FakeJobRepo(),
            summary_repo=FakeSummaryRepo(),
            analysis_repo=FakeAnalysisRepo(),
            llm_service=llm or FakeLLM(_payload()),
            event_publisher=RecordingEventPublisher(),
            candidate_profile_repo=FakeCandidateProfileRepo(None),
        )

    def test_successful_execution(self):
        graph = self._build()
        state = graph.invoke(_state())

        assert state.status == ExecutionStatus.COMPLETED
        assert state.analysis_result is not None
        assert state.analysis_result["scores"]["overall"] == 79
        assert state.analysis_result["recommendation"] == "consider"
        assert len(state.analysis_result["skills"]) == 2
        assert state.persisted is True

    def test_failed_analysis_when_llm_raises(self):
        graph = self._build(llm=FakeLLM(error=RuntimeError("provider down")))
        state = graph.invoke(_state())

        assert state.status == ExecutionStatus.FAILED
        assert any("provider down" in e for e in state.errors)
        assert state.persisted is False

    def test_failed_when_job_not_found(self):
        graph = self._build(job=None)
        state = graph.invoke(_state())

        assert state.status == ExecutionStatus.FAILED
        assert any("not found" in e for e in state.errors)

    def test_persist_failure_fails_execution(self):
        graph = self._build(persist_error=RuntimeError("constraint violated"))
        state = graph.invoke(_state())

        assert state.status == ExecutionStatus.FAILED
        assert state.persisted is False
        assert any("persist" in e and "constraint violated" in e for e in state.errors)
