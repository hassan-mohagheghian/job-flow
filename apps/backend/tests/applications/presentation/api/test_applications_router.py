"""Tests for the Applications API router.

Covers:
- Create / get-by-job / update application
- Follow-ups CRUD
- Document update / delete
- Generation dispatch (roadmap + documents) → creates ProcessingExecution
- Invalid input handling
"""

from __future__ import annotations

import uuid

import pytest

from applications.infrastructure.models.application_model import (
    ApplicationDocumentModel,
    ApplicationFollowUpModel,
    ApplicationModel,
    ApplicationStatusEventModel,
)
from jobs.infrastructure.models.job_model import JobModel
from processing.infrastructure.models.processing_execution_model import ProcessingExecutionModel


def _create_job(sa_session, **kwargs) -> JobModel:
    defaults = dict(
        id=str(uuid.uuid7()),
        url="https://example.com/job",
        title="Software Engineer",
        role="SWE",
        company="Tech Corp",
        location="Berlin",
        work_types=["Remote"],
        employment_types=["Full-time"],
        status="imported",
        deleted=0,
        workflow_log="[]",
        rescoring=0,
        user_id="test-user",
    )
    defaults.update(kwargs)
    defaults.pop("num", None)
    job = JobModel(**defaults)
    sa_session.add(job)
    sa_session.commit()
    return job


def _create_application(sa_session, job_id: str, **kwargs) -> ApplicationModel:
    defaults = dict(
        id=str(uuid.uuid7()),
        job_id=job_id,
        status="seen",
        user_id="test-user",
    )
    defaults.update(kwargs)
    app = ApplicationModel(**defaults)
    sa_session.add(app)
    sa_session.flush()
    sa_session.add(
        ApplicationStatusEventModel(
            id=str(uuid.uuid7()),
            application_id=app.id,
            status=app.status,
            changed_at="2026-08-01T09:00:00+00:00",
        )
    )
    sa_session.commit()
    return app


class TestApplicationAPI:
    def test_create_application(self, client, sa_session):
        job = _create_job(sa_session)
        resp = client.post("/api/applications", json={"job_id": job.id})
        assert resp.status_code == 201
        body = resp.json()
        assert body["job_id"] == job.id
        assert body["status"] == "seen"
        assert body["follow_ups"] == []
        assert body["documents"] == []
        assert len(body["status_timeline"]) == 1
        assert body["status_timeline"][0]["status"] == "seen"
        assert body["status_timeline"][0]["changed_at"] is not None

    def test_create_application_with_seen_at(self, client, sa_session):
        job = _create_job(sa_session)
        resp = client.post(
            "/api/applications",
            json={"job_id": job.id, "seen_at": "2026-07-01T08:00:00+00:00"},
        )
        assert resp.status_code == 201
        assert resp.json()["status_timeline"][0]["changed_at"] == "2026-07-01T08:00:00+00:00"

    def test_create_is_idempotent(self, client, sa_session):
        job = _create_job(sa_session)
        first = client.post("/api/applications", json={"job_id": job.id}).json()
        second = client.post("/api/applications", json={"job_id": job.id}).json()
        assert second["id"] == first["id"]

    def test_get_application_by_job(self, client, sa_session):
        job = _create_job(sa_session)
        created = client.post("/api/applications", json={"job_id": job.id}).json()
        resp = client.get(f"/api/applications/by-job/{job.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_by_job_404_when_none(self, client):
        resp = client.get("/api/applications/by-job/some-missing-job")
        assert resp.status_code == 404

    def test_status_distribution_for_current_user(self, client, sa_session):
        first = _create_job(sa_session)
        second = _create_job(sa_session)
        third = _create_job(sa_session)
        _create_application(sa_session, first.id, status="applied")
        _create_application(sa_session, second.id, status="interview")
        _create_application(sa_session, third.id, status="rejected")
        _create_application(
            sa_session,
            _create_job(sa_session).id,
            status="offer",
            user_id="other-user",
        )

        resp = client.get("/api/applications/status-distribution")

        assert resp.status_code == 200
        assert resp.json() == {
            "items": [
                {"status": "applied", "count": 1},
                {"status": "interview", "count": 1},
                {"status": "rejected", "count": 1},
            ],
            "total": 3,
        }

    def test_status_distribution_empty(self, client):
        resp = client.get("/api/applications/status-distribution")

        assert resp.status_code == 200
        assert resp.json() == {"items": [], "total": 0}

    def test_update_status(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        resp = client.patch(f"/api/applications/{app.id}", json={"status": "applied", "applied_at": "2026-08-01"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "applied"
        assert body["applied_at"] == "2026-08-01"
        timeline = body["status_timeline"]
        assert [e["status"] for e in timeline] == ["seen", "applied"]
        assert timeline[1]["changed_at"] is not None

    def test_update_status_with_timeline_at(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        resp = client.patch(
            f"/api/applications/{app.id}",
            json={"status": "applied", "timeline_at": "2026-08-05T09:00:00+00:00"},
        )
        assert resp.status_code == 200
        timeline = resp.json()["status_timeline"]
        applied = next(e for e in timeline if e["status"] == "applied")
        assert applied["changed_at"] == "2026-08-05T09:00:00+00:00"

    def test_update_status_event_changed_at(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        event = ApplicationStatusEventModel(
            id=str(uuid.uuid7()),
            application_id=app.id,
            status="applied",
            changed_at="2026-08-01T09:00:00+00:00",
        )
        sa_session.add(event)
        sa_session.commit()
        resp = client.patch(
            f"/api/applications/timeline/{event.id}",
            json={"changed_at": "2026-08-02T10:30:00+00:00"},
        )
        assert resp.status_code == 200
        assert resp.json()["changed_at"] == "2026-08-02T10:30:00+00:00"

    def test_update_status_event_missing_404(self, client):
        resp = client.patch("/api/applications/timeline/nope", json={"changed_at": "2026-08-02"})
        assert resp.status_code == 404

    def test_delete_status_event(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        event = ApplicationStatusEventModel(
            id=str(uuid.uuid7()),
            application_id=app.id,
            status="applied",
            changed_at="2026-08-01T09:00:00+00:00",
        )
        sa_session.add(event)
        sa_session.commit()
        event_id = str(event.id)
        resp = client.delete(f"/api/applications/timeline/{event_id}")
        assert resp.status_code == 204
        assert sa_session.query(ApplicationStatusEventModel).filter(
            ApplicationStatusEventModel.id == event_id
        ).first() is None

    def test_delete_status_event_missing_404(self, client):
        resp = client.delete("/api/applications/timeline/nope")
        assert resp.status_code == 404

    def test_delete_last_node_rolls_back_status(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        event = ApplicationStatusEventModel(
            id=str(uuid.uuid7()),
            application_id=app.id,
            status="applied",
            changed_at="2026-08-05T09:00:00+00:00",
        )
        sa_session.add(event)
        sa_session.commit()
        event_id = str(event.id)
        resp = client.delete(f"/api/applications/timeline/{event_id}")
        assert resp.status_code == 204
        sa_session.expire_all()
        assert sa_session.get(ApplicationModel, app.id).status == "seen"

    def test_delete_seen_node_rejected(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        seen = sa_session.query(ApplicationStatusEventModel).filter(
            ApplicationStatusEventModel.application_id == app.id
        ).first()
        resp = client.delete(f"/api/applications/timeline/{seen.id}")
        assert resp.status_code == 422
        sa_session.expire_all()
        assert sa_session.get(ApplicationStatusEventModel, seen.id) is not None

    def test_update_invalid_status_422(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        resp = client.patch(f"/api/applications/{app.id}", json={"status": "bogus"})
        assert resp.status_code == 422

    def test_update_missing_404(self, client):
        resp = client.patch("/api/applications/nope", json={"status": "applied"})
        assert resp.status_code == 404


class TestFollowUpAPI:
    def test_add_and_list(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        resp = client.post(
            f"/api/applications/{app.id}/follow-ups",
            json={"scheduled_at": "2026-08-10", "note": "Nudge recruiter"},
        )
        assert resp.status_code == 201
        fu = resp.json()
        assert fu["note"] == "Nudge recruiter"

        detail = client.get(f"/api/applications/by-job/{job.id}").json()
        assert len(detail["follow_ups"]) == 1

    def test_complete_follow_up(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        fu = client.post(
            f"/api/applications/{app.id}/follow-ups", json={"note": "nudge"}
        ).json()
        resp = client.patch(f"/api/applications/follow-ups/{fu['id']}", json={"completed": True})
        assert resp.status_code == 200
        assert resp.json()["completed_at"] is not None

    def test_delete_follow_up(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        fu = client.post(
            f"/api/applications/{app.id}/follow-ups", json={"note": "nudge"}
        ).json()
        resp = client.delete(f"/api/applications/follow-ups/{fu['id']}")
        assert resp.status_code == 204
        assert sa_session.query(ApplicationFollowUpModel).filter(
            ApplicationFollowUpModel.id == fu["id"]
        ).first() is None


class TestNoteAPI:
    def test_add_note_and_list_in_detail(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        resp = client.post(
            f"/api/applications/{app.id}/notes",
            json={"content": "Called recruiter, positive signal"},
        )
        assert resp.status_code == 201
        note = resp.json()
        assert note["content"] == "Called recruiter, positive signal"
        assert note["application_id"] == app.id
        assert note["created_at"]

        detail = client.get(f"/api/applications/by-job/{job.id}").json()
        assert len(detail["notes"]) == 1
        assert detail["notes"][0]["content"] == "Called recruiter, positive signal"

    def test_notes_newest_first(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        first = client.post(f"/api/applications/{app.id}/notes", json={"content": "first"}).json()
        second = client.post(f"/api/applications/{app.id}/notes", json={"content": "second"}).json()
        detail = client.get(f"/api/applications/by-job/{job.id}").json()
        ids = [n["id"] for n in detail["notes"]]
        assert ids == [second["id"], first["id"]]

    def test_add_note_empty_content_422(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        resp = client.post(f"/api/applications/{app.id}/notes", json={"content": "   "})
        assert resp.status_code == 422

    def test_add_note_missing_application_404(self, client):
        resp = client.post("/api/applications/nope/notes", json={"content": "hi"})
        assert resp.status_code == 404

    def test_delete_note(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        note = client.post(f"/api/applications/{app.id}/notes", json={"content": "n"}).json()
        resp = client.delete(f"/api/applications/notes/{note['id']}")
        assert resp.status_code == 204
        detail = client.get(f"/api/applications/by-job/{job.id}").json()
        assert detail["notes"] == []

    def test_delete_note_missing_404(self, client):
        resp = client.delete("/api/applications/notes/nope")
        assert resp.status_code == 404


class TestDocumentAPI:
    def test_update_document(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        doc = ApplicationDocumentModel(
            id=str(uuid.uuid7()),
            application_id=app.id,
            document_type="cover_letter",
            version=1,
            content="draft",
        )
        sa_session.add(doc)
        sa_session.commit()

        resp = client.patch(f"/api/applications/documents/{doc.id}", json={"content": "## Final letter"})
        assert resp.status_code == 200
        assert resp.json()["content"] == "## Final letter"

    def test_document_detail_substitutes_placeholders(self, client, sa_session):
        from placeholders.infrastructure.models.placeholder_model import PlaceholderModel
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        sa_session.add(PlaceholderModel(key="name", value="Hassan", user_id="test-user"))
        sa_session.add(
            ApplicationDocumentModel(
                id=str(uuid.uuid7()),
                application_id=app.id,
                document_type="tailored_resume",
                version=1,
                content="# {{name}}\n\nEngineer",
            )
        )
        sa_session.commit()
        detail = client.get(f"/api/applications/by-job/{job.id}").json()
        assert detail["documents"][0]["content"] == "# Hassan\n\nEngineer"

    def test_download_document_pdf(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        doc = ApplicationDocumentModel(
            id=str(uuid.uuid7()),
            application_id=app.id,
            document_type="tailored_resume",
            version=1,
            content="# Hassan\n\nSenior Engineer",
        )
        sa_session.add(doc)
        sa_session.commit()
        resp = client.get(f"/api/applications/documents/{doc.id}/pdf")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/pdf")
        assert resp.content.startswith(b"%PDF")
        assert "filename=" in resp.headers["content-disposition"]

    def test_download_document_pdf_missing_404(self, client):
        resp = client.get("/api/applications/documents/nope/pdf")
        assert resp.status_code == 404

    def test_update_document_empty_400(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        doc = ApplicationDocumentModel(
            id=str(uuid.uuid7()),
            application_id=app.id,
            document_type="tailored_resume",
            version=1,
            content="draft",
        )
        sa_session.add(doc)
        sa_session.commit()
        resp = client.patch(f"/api/applications/documents/{doc.id}", json={"content": "  "})
        assert resp.status_code == 422

    def test_delete_document(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        doc = ApplicationDocumentModel(
            id=str(uuid.uuid7()),
            application_id=app.id,
            document_type="cover_letter",
            version=1,
            content="draft",
        )
        sa_session.add(doc)
        sa_session.commit()
        doc_id = str(doc.id)
        resp = client.delete(f"/api/applications/documents/{doc_id}")
        assert resp.status_code == 200
        sa_session.expire_all()
        assert sa_session.query(ApplicationDocumentModel).filter(
            ApplicationDocumentModel.id == doc_id
        ).first() is None


class TestGenerationDispatchAPI:
    def test_generate_roadmap_queues_execution(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        resp = client.post(f"/api/applications/{app.id}/roadmap/generate")
        assert resp.status_code == 202
        body = resp.json()
        assert body["artifact"] == "roadmap"
        assert body["status"] == "queued"
        execution = sa_session.query(ProcessingExecutionModel).filter(
            ProcessingExecutionModel.id == body["execution_id"]
        ).first()
        assert execution is not None
        assert execution.execution_type == "roadmap_generation"
        assert execution.target_type == "application"
        assert execution.target_id == app.id

    def test_generate_documents_queues_typed_executions(self, client, sa_session):
        job1 = _create_job(sa_session)
        job2 = _create_job(sa_session, url="https://other.example")
        app1 = _create_application(sa_session, job1.id)
        app2 = _create_application(sa_session, job2.id)
        resume = client.post(f"/api/applications/{app1.id}/documents/tailored_resume/generate")
        letter = client.post(f"/api/applications/{app2.id}/documents/cover_letter/generate")
        assert resume.status_code == 202
        assert letter.status_code == 202
        resume_exec = sa_session.query(ProcessingExecutionModel).filter(
            ProcessingExecutionModel.id == resume.json()["execution_id"]
        ).first()
        letter_exec = sa_session.query(ProcessingExecutionModel).filter(
            ProcessingExecutionModel.id == letter.json()["execution_id"]
        ).first()
        assert resume_exec.execution_type == "application_resume"
        assert letter_exec.execution_type == "application_cover_letter"

    def test_generate_invalid_document_type_400(self, client, sa_session):
        job = _create_job(sa_session)
        app = _create_application(sa_session, job.id)
        resp = client.post(f"/api/applications/{app.id}/documents/bogus/generate")
        assert resp.status_code == 400

    def test_generate_missing_application_404(self, client):
        resp = client.post("/api/applications/nope/roadmap/generate")
        assert resp.status_code == 404
