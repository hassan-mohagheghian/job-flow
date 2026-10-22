"""Tests for the Roadmap Generation workflow.

Covers:
- Prompt builders + output schema (priority enum, shape)
- Validation models (RoadmapOutput round-trip, empty/invalid rejection)
- Nodes (LoadContext, Generate, Persist) with fake repos + mock LLM
- The RoadmapGenerationGraph end-to-end (context → one LLM call → persisted)
- The roadmap workflow step mapper + progress_ops dispatch
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from processing.application.services.roadmap_generation_prompts import (
    ROADMAP_GENERATION_PROMPT_VERSION,
    ROADMAP_GENERATION_SCHEMA_VERSION,
    build_roadmap_output_schema,
    build_roadmap_prompt,
)
from processing.application.services.roadmap_generation_validation import (
    RoadmapOutput,
)
from processing.application.workflows import progress_ops
from processing.application.workflows.roadmap_generation import RoadmapGenerationGraph
from processing.application.workflows.roadmap_generation.nodes import (
    ExecutionFailedNode,
    GenerateNode,
    LoadContextNode,
    PersistNode,
    RoadmapReadyNode,
)
from processing.application.workflows.roadmap_workflow_step_mapper import (
    RoadmapWorkflowStepMapper,
)
from processing.domain.enums import ExecutionStatus, ExecutionType
from processing.domain.workflow.roadmap_generation_state import (
    RoadmapGenerationState,
)
from roadmaps.application.services.roadmap_service import RoadmapService
from roadmaps.domain.event_publisher import InMemoryEventCollector


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


class FakeRoadmapRepo:
    """In-memory roadmap repository supporting the PersistNode surface."""

    def __init__(self):
        self.roadmaps: dict[str, dict] = {}
        self.goals: dict[str, dict] = {}
        self.milestones: dict[str, dict] = {}
        self.tasks: dict[str, dict] = {}
        self.skill_links: dict[str, dict] = {}
        self._n = 0

    def _id(self, prefix):
        self._n += 1
        return f"{prefix}-{self._n}"

    def create(self, data):
        row = dict(data)
        row["id"] = self._id("roadmap")
        self.roadmaps[row["id"]] = row
        return row

    def get_by_id(self, roadmap_id):
        return self.roadmaps.get(roadmap_id)

    def create_goal(self, data):
        row = dict(data)
        row["id"] = self._id("goal")
        self.goals[row["id"]] = row
        return row

    def get_goal(self, roadmap_id):
        return next((g for g in self.goals.values() if g["roadmap_id"] == roadmap_id), None)

    def list_milestones(self, roadmap_id):
        return [m for m in self.milestones.values() if m["roadmap_id"] == roadmap_id]

    def create_milestone(self, data):
        row = dict(data)
        row["id"] = self._id("milestone")
        self.milestones[row["id"]] = row
        return row

    def get_milestone(self, milestone_id):
        return self.milestones.get(milestone_id)

    def list_tasks(self, milestone_id):
        return [t for t in self.tasks.values() if t["milestone_id"] == milestone_id]

    def create_task(self, data):
        row = dict(data)
        row["id"] = self._id("task")
        self.tasks[row["id"]] = row
        return row

    def list_skills(self, roadmap_id):
        return [s for s in self.skill_links.values() if s["roadmap_id"] == roadmap_id]

    def create_skill_link(self, data):
        row = dict(data)
        row["id"] = self._id("link")
        self.skill_links[row["id"]] = row
        return row


class FakeSkillRepo:
    def __init__(self):
        self.resolved: list[str] = []
        self._n = 0

    def resolve_skill(self, data):
        self._n += 1
        self.resolved.append(str(data.get("name")))
        return self._n


def _roadmap_service():
    repo = FakeRoadmapRepo()
    collector = InMemoryEventCollector()
    service = RoadmapService(repo, FakeSkillRepo(), collector)
    return service, repo, collector


def _valid_payload() -> dict:
    return {
        "title": "Kafka Readiness",
        "goal": {"type": "JOB", "title": "Get the job", "description": "Land the staff role"},
        "milestones": [
            {
                "title": "Ship a Kafka project",
                "description": "Build a real-time pipeline",
                "priority": "critical",
                "success_criteria": "A working producer/consumer demo",
                "skills": ["kafka"],
                "tasks": [
                    {
                        "title": "Build producer",
                        "description": "Write a Kafka producer in Python",
                        "estimated_effort": "3-4 hours",
                        "success_criteria": "Messages land in a topic",
                    }
                ],
            }
        ],
    }


def _context() -> dict[str, str]:
    from processing.application.services.application_intelligence_inputs import (
        build_application_context,
    )

    return build_application_context(_job(), _analysis(), _company(), _intelligence(), _profile())


def _state() -> RoadmapGenerationState:
    return RoadmapGenerationState(
        execution_id="exec-1",
        application_id="app-1",
        job_id="",
        intent=ExecutionType.ROADMAP_GENERATION.value,
    )


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
# Prompt builders + schema
# --------------------------------------------------------------------------- #


class TestPrompts:
    def test_schema_shape(self):
        schema = build_roadmap_output_schema()
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "title" in props
        assert "goal" in props
        assert props["goal"]["properties"]["type"]["enum"] == ["JOB"]
        assert "milestones" in props
        assert props["milestones"]["type"] == "array"

    def test_milestone_schema_priority_enum(self):
        schema = build_roadmap_output_schema()
        milestone = schema["properties"]["milestones"]["items"]
        assert milestone["properties"]["priority"]["enum"] == ["critical", "high", "medium", "low"]
        assert "skills" in milestone["properties"]
        assert milestone["properties"]["tasks"]["items"]["required"] == ["title"]

    def test_schema_requires_milestones(self):
        schema = build_roadmap_output_schema()
        assert schema["required"] == ["milestones"]

    def test_prompt_grounded_and_rule_based(self):
        prompt = build_roadmap_prompt(_context())
        assert "Acme GmbH" in prompt
        assert "kafka" in prompt
        assert "Hassan" in prompt
        assert "milestones:" in prompt
        assert "priority" in prompt

    def test_missing_context_falls_back_gracefully(self):
        prompt = build_roadmap_prompt({"job": "", "job_skills": None})
        assert "no data available" in prompt

    def test_prompt_and_schema_versions(self):
        assert ROADMAP_GENERATION_PROMPT_VERSION == "1.0.1"
        assert ROADMAP_GENERATION_SCHEMA_VERSION == "1.0.0"


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #


class TestValidation:
    def test_valid_payload_round_trip(self):
        out = RoadmapOutput.model_validate(_valid_payload())
        payload = out.dump_payload()
        assert payload["title"] == "Kafka Readiness"
        assert payload["goal"]["type"] == "JOB"
        assert len(payload["milestones"]) == 1
        assert payload["milestones"][0]["priority"] == "critical"
        assert payload["milestones"][0]["skills"] == ["kafka"]
        assert payload["milestones"][0]["tasks"][0]["estimated_effort"] == "3-4 hours"

    def test_priority_lowercased_and_validated(self):
        out = RoadmapOutput.model_validate(
            {"milestones": [{"title": "M", "priority": "HIGH"}]}
        )
        assert out.milestones[0].priority == "high"

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValidationError):
            RoadmapOutput.model_validate(
                {"milestones": [{"title": "M", "priority": "urgent"}]}
            )

    def test_empty_milestones_rejected(self):
        with pytest.raises(ValidationError):
            RoadmapOutput.model_validate({"title": "X", "milestones": []})

    def test_missing_milestones_rejected(self):
        with pytest.raises(ValidationError):
            RoadmapOutput.model_validate({"title": "X"})

    def test_empty_task_title_rejected(self):
        with pytest.raises(ValidationError):
            RoadmapOutput.model_validate(
                {"milestones": [{"title": "M", "tasks": [{"title": "  "}]}]}
            )

    def test_milestones_capped_at_eight(self):
        milestones = [{"title": f"M{i}"} for i in range(12)]
        out = RoadmapOutput.model_validate({"milestones": milestones})
        assert len(out.milestones) == 8


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
    def _ready_state(self) -> RoadmapGenerationState:
        state = _state()
        state.context = _context()
        return state

    def test_generates_roadmap_payload(self):
        state = GenerateNode(FakeLLM(content=json.dumps(_valid_payload())))(self._ready_state())
        assert state.status != ExecutionStatus.FAILED
        assert state.result["title"] == "Kafka Readiness"
        assert state.result["milestones"][0]["priority"] == "critical"
        assert state.result.get("prompt_version") == "1.0.1"

    def test_llm_error_fails_clean(self):
        state = GenerateNode(FakeLLM(error=RuntimeError("provider down")))(self._ready_state())
        assert state.status == ExecutionStatus.FAILED
        assert any("provider down" in e for e in state.errors)

    def test_schema_invalid_fails_clean(self):
        llm = FakeLLM(content=json.dumps({"title": "X", "milestones": []}))
        state = GenerateNode(llm)(self._ready_state())
        assert state.status == ExecutionStatus.FAILED
        assert any("does not match the required format" in e for e in state.errors)

    def test_retries_once_then_succeeds(self):
        class FlakyLLM(FakeLLM):
            def __init__(self):
                super().__init__(content=json.dumps(_valid_payload()))
                self._fail_first = True

            def generate_structured(self, prompt, schema=None, timeout=None):
                if self._fail_first:
                    self._fail_first = False
                    self.calls.append({"prompt": prompt, "schema": schema, "timeout": timeout})
                    raise RuntimeError("Failed to parse opencode JSON output\nRaw output: {truncated")
                return super().generate_structured(prompt, schema=schema, timeout=timeout)

        state = GenerateNode(FlakyLLM())(self._ready_state())
        assert state.status != ExecutionStatus.FAILED
        assert state.result["title"] == "Kafka Readiness"


# --------------------------------------------------------------------------- #
# PersistNode
# --------------------------------------------------------------------------- #


class TestPersistNode:
    def _ready_state(self) -> RoadmapGenerationState:
        state = _state()
        state.job_id = "job-uuid-1"
        state.context = _context()
        state.result = _valid_payload()
        return state

    def test_persists_roadmap_and_children(self):
        service, repo, collector = _roadmap_service()
        state = PersistNode(service, FakeJobService(_job()), collector)(self._ready_state())

        assert state.status != ExecutionStatus.FAILED
        assert state.persisted_roadmap_id is not None
        roadmap = repo.roadmaps[state.persisted_roadmap_id]
        assert roadmap["source"] == "APPLICATION"
        assert roadmap["application_id"] == "app-1"
        assert roadmap["title"] == "Kafka Readiness"
        goal = repo.get_goal(state.persisted_roadmap_id)
        assert goal["type"] == "JOB"
        assert goal["target_job_id"] == "job-uuid-1"
        assert goal["target_company_id"] == "company-uuid-1"

        milestones = repo.list_milestones(state.persisted_roadmap_id)
        assert len(milestones) == 1
        assert milestones[0]["title"] == "Ship a Kafka project"
        assert milestones[0]["priority"] == "CRITICAL"
        tasks = repo.list_tasks(milestones[0]["id"])
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Build producer"
        assert tasks[0]["estimated_effort"] == "3-4 hours"
        skills = repo.list_skills(state.persisted_roadmap_id)
        assert len(skills) == 1
        assert skills[0]["skill_name"] == "kafka"
        assert skills[0]["milestone_id"] == milestones[0]["id"]

    def test_emits_domain_events(self):
        service, _, collector = _roadmap_service()
        state = PersistNode(service, FakeJobService(_job()), collector)(self._ready_state())

        event_types = {e.event_type for e in collector.events}
        assert "roadmap.created" in event_types
        assert "roadmap.milestone.added" in event_types
        assert "roadmap.task.added" in event_types
        assert "roadmap.skill.linked" in event_types

    def test_no_result_fails(self):
        service, _, _ = _roadmap_service()
        state = _state()
        state.context = _context()
        state = PersistNode(service, FakeJobService(_job()))(state)
        assert state.status == ExecutionStatus.FAILED

    def test_service_failure_fails_state(self):
        class BoomService:
            def create_from_application(self, **kwargs):
                raise RuntimeError("db down")

        state = PersistNode(BoomService(), FakeJobService(_job()))(self._ready_state())
        assert state.status == ExecutionStatus.FAILED
        assert any("Failed to persist roadmap" in e for e in state.errors)


# --------------------------------------------------------------------------- #
# Graph E2E
# --------------------------------------------------------------------------- #


class TestGraphE2E:
    def _graph(self, llm=None):
        service, _, _ = _roadmap_service()
        return RoadmapGenerationGraph(
            FakeApplicationRepo({"id": "app-1", "job_id": "job-uuid-1"}),
            FakeJobService(_job()),
            FakeAnalysisRepo(_analysis()),
            FakeCompanyService(_company()),
            FakeIntelligenceRepo(_intelligence()),
            FakeProfileRepo(_profile()),
            service,
            llm_service=llm or FakeLLM(content=json.dumps(_valid_payload())),
            event_publisher=RecordingEventPublisher(),
        )

    def test_end_to_end(self):
        llm = FakeLLM(content=json.dumps(_valid_payload()))
        state = self._graph(llm).invoke(_state())
        assert state.status == ExecutionStatus.COMPLETED
        assert state.persisted_roadmap_id is not None
        assert len(llm.calls) == 1

    def test_failure_routes_to_execution_failed(self):
        graph = self._graph(llm=FakeLLM(error=RuntimeError("boom")))
        state = graph.invoke(_state())
        assert state.status == ExecutionStatus.FAILED
        assert state.persisted_roadmap_id is None

    def test_load_failure_routes_to_execution_failed(self):
        graph = RoadmapGenerationGraph(
            FakeApplicationRepo(None),
            FakeJobService(_job()),
            FakeAnalysisRepo(_analysis()),
            FakeCompanyService(_company()),
            FakeIntelligenceRepo(_intelligence()),
            FakeProfileRepo(_profile()),
            _roadmap_service()[0],
            llm_service=FakeLLM(content=json.dumps(_valid_payload())),
            event_publisher=RecordingEventPublisher(),
        )
        state = graph.invoke(_state())
        assert state.status == ExecutionStatus.FAILED


# --------------------------------------------------------------------------- #
# Terminal nodes
# --------------------------------------------------------------------------- #


class TestTerminalNodes:
    def test_roadmap_ready_sets_completed(self):
        state = RoadmapReadyNode()(_state())
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
        mapper = RoadmapWorkflowStepMapper
        assert mapper.step_for_node("generate") == ("generate", "Generate")
        assert mapper.step_for_node("persist") == ("persist", "Save Result")
        assert mapper.is_displayable("generate") is True
        assert mapper.is_displayable("execution_failed") is False
        assert mapper.is_displayable("roadmap_ready") is False

    def test_initial_progress_shape(self):
        progress = RoadmapWorkflowStepMapper.build_initial_progress("exec-1")
        assert progress.id == "roadmap_generation"
        ids = [s.id for s in progress.steps]
        assert ids == ["load_context", "generate", "persist"]
        assert progress.progress == 0.0

    def test_progress_ops_dispatches_roadmap(self):
        state = _state()
        progress = progress_ops._build_initial_progress(state)
        assert progress.id == "roadmap_generation"

    def test_progress_ops_build_initial_progress_roadmap_type(self):
        progress = progress_ops.build_initial_progress("exec-1", target_type="roadmap")
        assert progress.id == "roadmap_generation"