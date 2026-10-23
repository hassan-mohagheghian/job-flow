"""Tests for the Application Intelligence workflow.

Covers:
- Context assembly (grounded consumers — no re-analysis)
- Prompt builders (resume / cover letter) + output schemas
- Validation models (DocumentOutput)
- Nodes (LoadContext, Generate, Persist) with fake repos + mock LLM
- The ApplicationIntelligenceGraph end-to-end
- The application workflow step mapper + progress_ops dispatch
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from processing.application.services.application_intelligence_inputs import (
    build_application_context,
    build_candidate_context,
    build_company_context,
    build_job_context,
    build_job_skills_context,
)
from processing.application.services.application_intelligence_prompts import (
    APPLICATION_INTELLIGENCE_PROMPT_VERSION,
    build_cover_letter_prompt,
    build_document_output_schema,
    build_resume_prompt,
)
from processing.application.services.application_intelligence_validation import (
    DocumentOutput,
)
from processing.application.workflows.application_intelligence import ApplicationIntelligenceGraph
from processing.application.workflows.application_intelligence.nodes import (
    ApplicationReadyNode,
    ExecutionFailedNode,
    GenerateNode,
    LoadContextNode,
    PersistNode,
)
from processing.application.workflows.application_workflow_step_mapper import (
    ApplicationWorkflowStepMapper,
)
from processing.application.workflows import progress_ops
from processing.domain.enums import ExecutionStatus, ExecutionType
from processing.domain.workflow.application_intelligence_state import (
    ApplicationIntelligenceState,
)


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


def _job(**overrides) -> dict:
    data = {
        "id": "job-uuid-1",
        "title": "Senior Backend Engineer",
        "company": "Acme GmbH",
        "company_id": "company-uuid-1",
        "location": "Berlin, Germany",
        "salary": "90k",
        "visa": "sponsored",
        "industry": "fintech",
        "domain": "payments",
        "description": "Python, Postgres, Kafka.",
    }
    data.update(overrides)
    return data


def _analysis(**overrides) -> dict:
    payload = {
        "scores": {"fit": 85, "success": 70},
        "scores_explanation": {
            "fit_factors": ["Python backend"],
            "success_factors": ["Senior level"],
            "concerns": ["No Kafka"],
        },
        "recommendation": "apply",
        "apply_reason": "Strong stack overlap.",
        "summary": {"summary": "Backend role at Acme.", "resume_fit": "Strong fit.", "note": ""},
        "skills": [
            {"name": "python", "category": "backend", "level": 4, "status": "matched", "evidence": "posted"},
            {"name": "kafka", "category": "data", "level": 1, "status": "missing", "evidence": "posted"},
        ],
        "insights": ["Mention Kafka coursework"],
    }
    data = {"job_id": "job-uuid-1", "payload": payload, "generated_at": "2026-01-01T00:00:00Z"}
    data.update(overrides)
    return data


def _company(**overrides) -> dict:
    data = {
        "id": "company-uuid-1",
        "name": "Acme GmbH",
        "website": "https://acme.de",
        "domain": "acme.de",
        "country": "Germany",
    }
    data.update(overrides)
    return data


def _intelligence(**overrides) -> dict:
    data = {
        "company_id": "company-uuid-1",
        "overview": "A Berlin fintech building payment rails.",
        "technology_analysis": "Python, Kafka, Kubernetes.",
        "culture_analysis": "Collaborative, async.",
        "benefits_analysis": "Relocation support.",
        "visa_analysis": "Full visa sponsorship.",
        "scores": {"fit": 90, "success": 75},
    }
    data.update(overrides)
    return data


def _profile(**overrides) -> dict:
    data = {
        "id": "profile-uuid-1",
        "name": "Hassan",
        "title": "Senior Software Engineer",
        "headline": "Backend engineer focused on Python and distributed systems.",
        "summary": "7 years building payment systems.",
        "skills": [
            {"name": "python", "level": 4, "years_of_experience": 7, "evidence": {"sources": ["resume"]}},
        ],
        "experiences": [
            {"company": "FinTech Co", "role": "Senior Engineer", "start_date": "2020", "end_date": None,
             "summary": "Built payment microservices in Python."},
        ],
    }
    data.update(overrides)
    return data


class FakeApplicationRepo:
    def __init__(self, application=None):
        self._app = application

    def get_by_id(self, application_id):
        return self._app


class FakeJobService:
    def __init__(self, job=None):
        self._job = job

    def get_job(self, job_id):
        return self._job


class FakeAnalysisRepo:
    def __init__(self, analysis=None):
        self._analysis = analysis

    def get_by_job_id(self, job_id):
        return self._analysis


class FakeCompanyService:
    def __init__(self, company=None):
        self._company = company

    def get_company(self, company_id):
        return self._company


class FakeIntelligenceRepo:
    def __init__(self, intelligence=None):
        self._intelligence = intelligence

    def get_by_company_id(self, company_id):
        return self._intelligence


class FakeProfileRepo:
    def __init__(self, profile=None):
        self._profile = profile

    def get_current_profile(self):
        return self._profile


class FakeDocumentRepo:
    def __init__(self):
        self.created = []

    def get_next_version(self, application_id, document_type):
        same = [d for d in self.created if d["document_type"] == document_type]
        return len(same) + 1

    def create(self, data):
        stored = dict(data, id=f"doc-{len(self.created) + 1}")
        self.created.append(stored)
        return stored


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


class RecordingEventPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event_name, execution_id, job_id, status, **kwargs):
        self.events.append((event_name, execution_id, job_id, status, kwargs))


class CollectingEventPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def _context() -> dict[str, str]:
    return build_application_context(_job(), _analysis(), _company(), _intelligence(), _profile())


def _state(intent: str = ExecutionType.APPLICATION_RESUME) -> ApplicationIntelligenceState:
    state = ApplicationIntelligenceState(
        execution_id="exec-1",
        application_id="app-1",
        job_id="job-uuid-1",
        intent=intent,
    )
    state.workflow_progress = progress_ops.build_initial_progress("exec-1", "application")
    return state


def _load_context_node() -> LoadContextNode:
    return LoadContextNode(
        FakeApplicationRepo({"id": "app-1", "job_id": "job-uuid-1"}),
        FakeJobService(_job()),
        FakeAnalysisRepo(_analysis()),
        FakeCompanyService(_company()),
        FakeIntelligenceRepo(_intelligence()),
        FakeProfileRepo(_profile()),
    )


# --------------------------------------------------------------------------- #
# Context assembly
# --------------------------------------------------------------------------- #


class TestContextAssembly:
    def test_job_context_includes_analysis(self):
        text = build_job_context(_job(), _analysis())
        assert "Acme GmbH" in text
        assert "JOB ANALYSIS" in text
        assert "fit score: 85" in text
        assert "recommendation: apply" in text

    def test_job_skills_context_tags_gaps(self):
        text = build_job_skills_context(_analysis())
        assert "kafka" in text
        assert "missing" in text
        assert "python" in text
        assert "matched" in text

    def test_company_context_includes_intelligence(self):
        text = build_company_context(_company(), _intelligence())
        assert "Acme GmbH" in text
        assert "COMPANY INTELLIGENCE" in text
        assert "visa sponsorship" in text

    def test_candidate_context_reuses_profile_builder(self):
        text = build_candidate_context(_profile())
        assert "CANDIDATE PROFILE" in text
        assert "Hassan" in text
        assert "python" in text

    def test_full_context_assembled(self):
        ctx = _context()
        assert ctx["job"] and ctx["job_skills"] and ctx["company"] and ctx["candidate"]
        assert "kafka" in ctx["job_skills"]

    def test_missing_analysis_falls_back_gracefully(self):
        text = build_job_context(_job(), None)
        assert "no structured analysis" in text

    def test_missing_intelligence_falls_back_gracefully(self):
        text = build_company_context(_company(), None)
        assert "no company intelligence" in text


# --------------------------------------------------------------------------- #
# Prompt builders + schemas
# --------------------------------------------------------------------------- #


class TestPrompts:
    def test_resume_prompt_tailored(self):
        prompt = build_resume_prompt(_context())
        assert "MARKDOWN" in prompt
        assert "Acme GmbH" in prompt
        assert "Hassan" in prompt
        assert "applying for a role" in prompt
        assert "visa-sponsored" not in prompt

    def test_cover_letter_prompt(self):
        prompt = build_cover_letter_prompt(_context())
        assert "Subject" in prompt
        assert "applying for a role" in prompt
        assert "visa-sponsored" not in prompt
        assert "350 words" in prompt

    def test_document_schema_shape(self):
        schema = build_document_output_schema()
        assert schema["required"] == ["content"]
        assert schema["properties"]["content"]["type"] == "string"

    def test_resume_prompt_instructs_contact_placeholders(self):
        prompt = build_resume_prompt(_context())
        assert "{{name}}" in prompt
        assert "{{email}}" in prompt
        assert "PLACEHOLDERS" in prompt

    def test_cover_letter_prompt_instructs_placeholders(self):
        prompt = build_cover_letter_prompt(_context())
        assert "{{name}}" in prompt
        assert "{{linkedin}}" in prompt

    def test_prompt_version_constant(self):
        assert APPLICATION_INTELLIGENCE_PROMPT_VERSION == "1.0.2"


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


class TestValidation:
    def test_document_output_valid(self):
        out = DocumentOutput.model_validate({"content": "## Hello"}).dump_payload()
        assert out["content"] == "## Hello"

    def test_document_output_rejects_empty(self):
        with pytest.raises(ValidationError):
            DocumentOutput.model_validate({"content": "  "})


# --------------------------------------------------------------------------- #
# LoadContextNode
# --------------------------------------------------------------------------- #


class TestLoadContextNode:
    def test_loads_context(self):
        state = _load_context_node()(_state())
        assert state.status != ExecutionStatus.FAILED
        assert state.job_id == "job-uuid-1"
        assert "job" in state.context
        assert "job_skills" in state.context
        assert "company" in state.context
        assert "candidate" in state.context

    def test_missing_application_fails(self):
        node = LoadContextNode(
            FakeApplicationRepo(None),
            FakeJobService(_job()),
            FakeAnalysisRepo(_analysis()),
            FakeCompanyService(_company()),
            FakeIntelligenceRepo(_intelligence()),
            FakeProfileRepo(_profile()),
        )
        state = node(_state())
        assert state.status == ExecutionStatus.FAILED
        assert any("not found" in e for e in state.errors)

    def test_application_without_job_fails(self):
        node = LoadContextNode(
            FakeApplicationRepo({"id": "app-1", "job_id": ""}),
            FakeJobService(_job()),
            FakeAnalysisRepo(_analysis()),
            FakeCompanyService(_company()),
            FakeIntelligenceRepo(_intelligence()),
            FakeProfileRepo(_profile()),
        )
        state = node(_state())
        assert state.status == ExecutionStatus.FAILED

    def test_missing_job_fails(self):
        node = LoadContextNode(
            FakeApplicationRepo({"id": "app-1", "job_id": "job-uuid-1"}),
            FakeJobService(None),
            FakeAnalysisRepo(_analysis()),
            FakeCompanyService(_company()),
            FakeIntelligenceRepo(_intelligence()),
            FakeProfileRepo(_profile()),
        )
        state = node(_state())
        assert state.status == ExecutionStatus.FAILED


# --------------------------------------------------------------------------- #
# GenerateNode
# --------------------------------------------------------------------------- #


class TestGenerateNode:
    def _ready_state(self):
        state = _state()
        state.context = _context()
        return state

    def test_resume_generation(self):
        state = _state(ExecutionType.APPLICATION_RESUME)
        state.context = _context()
        state = GenerateNode(FakeLLM(content=json.dumps({"content": "## Hassan"})))(state)
        assert state.status != ExecutionStatus.FAILED
        assert state.result["content"] == "## Hassan"

    def test_cover_letter_generation(self):
        state = _state(ExecutionType.APPLICATION_COVER_LETTER)
        state.context = _context()
        state = GenerateNode(FakeLLM(content=json.dumps({"content": "Dear Team"})))(state)
        assert state.status != ExecutionStatus.FAILED
        assert state.result["content"] == "Dear Team"

    def test_unsupported_intent_fails(self):
        state = _state("bogus_intent")
        state.context = _context()
        state = GenerateNode(FakeLLM(content="{}"))(state)
        assert state.status == ExecutionStatus.FAILED
        assert any("Unsupported intent" in e for e in state.errors)

    def test_llm_error_fails(self):
        state = GenerateNode(FakeLLM(error=RuntimeError("provider down")))(self._ready_state())
        assert state.status == ExecutionStatus.FAILED
        assert any("provider down" in e for e in state.errors)

    def test_schema_invalid_fails_clean(self):
        content = {"content": "  "}
        state = GenerateNode(FakeLLM(content=json.dumps(content)))(self._ready_state())
        assert state.status == ExecutionStatus.FAILED
        assert any("does not match the required format" in e for e in state.errors)

    def test_retries_once_then_succeeds(self):
        class FlakyLLM(FakeLLM):
            def __init__(self):
                super().__init__(content=json.dumps({"content": "## Hassan"}))
                self._fail_first = True

            def generate_structured(self, prompt, schema=None, timeout=None):
                if self._fail_first:
                    self._fail_first = False
                    self.calls.append({"prompt": prompt, "schema": schema, "timeout": timeout})
                    raise RuntimeError("Failed to parse opencode JSON output\nRaw output: {truncated")
                return super().generate_structured(prompt, schema=schema, timeout=timeout)

        state = GenerateNode(FlakyLLM())(self._ready_state())
        assert state.status != ExecutionStatus.FAILED
        assert state.result["content"] == "## Hassan"


# --------------------------------------------------------------------------- #
# PersistNode
# --------------------------------------------------------------------------- #


class TestPersistNode:
    def test_document_persisted_typed(self):
        publisher = CollectingEventPublisher()
        doc_repo = FakeDocumentRepo()
        state = _state(ExecutionType.APPLICATION_RESUME)
        state.result = {"content": "## Hassan"}
        state = PersistNode(doc_repo, publisher)(state)

        assert state.status != ExecutionStatus.FAILED
        assert state.persisted_id == "doc-1"
        assert doc_repo.created[0]["document_type"] == "tailored_resume"
        assert doc_repo.created[0]["content"] == "## Hassan"
        assert any(e.event_type == "application.document.generated" for e in publisher.events)

    def test_cover_letter_type(self):
        doc_repo = FakeDocumentRepo()
        state = _state(ExecutionType.APPLICATION_COVER_LETTER)
        state.result = {"content": "Dear Hiring Team"}
        state = PersistNode(doc_repo)(state)
        assert doc_repo.created[0]["document_type"] == "cover_letter"

    def test_no_result_fails(self):
        state = PersistNode(FakeDocumentRepo())(_state())
        assert state.status == ExecutionStatus.FAILED


# --------------------------------------------------------------------------- #
# Graph E2E
# --------------------------------------------------------------------------- #


class TestGraphE2E:
    def _graph(self, llm=None):
        return ApplicationIntelligenceGraph(
            FakeApplicationRepo({"id": "app-1", "job_id": "job-uuid-1"}),
            FakeJobService(_job()),
            FakeAnalysisRepo(_analysis()),
            FakeCompanyService(_company()),
            FakeIntelligenceRepo(_intelligence()),
            FakeProfileRepo(_profile()),
            FakeDocumentRepo(),
            llm_service=llm
            or FakeLLM(content=json.dumps({"content": "## Hassan"})),
            event_publisher=RecordingEventPublisher(),
        )

    def test_resume_end_to_end(self):
        state = self._graph().invoke(_state(ExecutionType.APPLICATION_RESUME))
        assert state.status == ExecutionStatus.COMPLETED
        assert state.persisted_id == "doc-1"
        assert state.result["content"] == "## Hassan"

    def test_cover_letter_end_to_end(self):
        llm = FakeLLM(content=json.dumps({"content": "Dear Team"}))
        state = self._graph(llm).invoke(_state(ExecutionType.APPLICATION_COVER_LETTER))
        assert state.status == ExecutionStatus.COMPLETED
        assert state.persisted_id == "doc-1"
        assert state.result["content"] == "Dear Team"

    def test_failure_routes_to_execution_failed(self):
        graph = self._graph(llm=FakeLLM(error=RuntimeError("boom")))
        state = graph.invoke(_state())
        assert state.status == ExecutionStatus.FAILED
        assert state.persisted_id is None

    def test_load_failure_routes_to_execution_failed(self):
        graph = ApplicationIntelligenceGraph(
            FakeApplicationRepo(None),
            FakeJobService(_job()),
            FakeAnalysisRepo(_analysis()),
            FakeCompanyService(_company()),
            FakeIntelligenceRepo(_intelligence()),
            FakeProfileRepo(_profile()),
            FakeDocumentRepo(),
            llm_service=FakeLLM(content="{}"),
            event_publisher=RecordingEventPublisher(),
        )
        state = graph.invoke(_state())
        assert state.status == ExecutionStatus.FAILED


# --------------------------------------------------------------------------- #
# Terminal nodes
# --------------------------------------------------------------------------- #


class TestTerminalNodes:
    def test_application_ready_sets_completed(self):
        state = ApplicationReadyNode()(_state())
        assert state.status == ExecutionStatus.COMPLETED

    def test_execution_failed_marks_failed(self):
        state = _state()
        state.errors.append("boom")
        state = ExecutionFailedNode()(state)
        assert state.status == ExecutionStatus.FAILED


# --------------------------------------------------------------------------- #
# Step mapper + progress dispatch
# --------------------------------------------------------------------------- #


class TestStepMapper:
    def test_step_mapping(self):
        mapper = ApplicationWorkflowStepMapper
        assert mapper.step_for_node("generate") == ("generate", "Generate")
        assert mapper.step_for_node("persist") == ("persist", "Save Result")
        assert mapper.is_displayable("generate") is True
        assert mapper.is_displayable("execution_failed") is False
        assert mapper.is_displayable("application_ready") is False

    def test_initial_progress_shape(self):
        progress = ApplicationWorkflowStepMapper.build_initial_progress("exec-1")
        assert progress.id == "application_generation"
        ids = [s.id for s in progress.steps]
        assert ids == ["load_context", "generate", "persist"]
        assert progress.progress == 0.0

    def test_progress_ops_dispatches_application(self):
        state = _state()
        progress = progress_ops._build_initial_progress(state)
        assert progress.id == "application_generation"

    def test_progress_ops_target_type_application(self):
        state = _state()
        assert progress_ops._target_type(state) == "application"
        assert progress_ops._target_id(state) == "app-1"
