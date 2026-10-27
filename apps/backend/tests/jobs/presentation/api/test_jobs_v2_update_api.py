"""Tests for the Edit Job API (PATCH /api/jobs/{job_id})."""
import json

from jobs.infrastructure.models.job_model import JobModel


def _create_job(test_db, **kwargs) -> JobModel:
    defaults = dict(
        id=None,
        url="https://example.com/job",
        title="Software Engineer",
        role="SWE",
        company="Tech Corp",
        location="Berlin",
        work_types=["Remote"],
        employment_types=["Full-time"],
        visa="Yes",
        salary="90-110",
        description="original description",
        status="imported",
        deleted=0,
        workflow_log="[]",
        rescoring=0,
        user_id="test-user",
    )
    defaults.update(kwargs)
    if defaults["id"] is None:
        import uuid
        defaults["id"] = str(uuid.uuid7())
    job = JobModel(**defaults)
    test_db.add(job)
    test_db.commit()
    return job


class TestEditJobAPI:
    def test_update_fields(self, client, test_db):
        job = _create_job(test_db, title="Old Title", company="Old Co")
        job_id = job.id

        resp = client.patch(f"/api/jobs/{job_id}", json={
            "title": "New Title",
            "company": "New Co",
            "location": "Munich",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert data["title"] == "New Title"
        assert data["company_name"] == "New Co"
        assert data["location"] == "Munich"

    def test_unchanged_fields_preserved(self, client, test_db):
        job = _create_job(test_db, title="Keep", visa="Yes", salary="90k")
        resp = client.patch(f"/api/jobs/{job.id}", json={"title": "Changed"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Changed"
        assert data["visa"] == "Yes"
        assert data["salary"] == "90k"

    def test_empty_payload_is_noop(self, client, test_db):
        job = _create_job(test_db, title="Original")
        resp = client.patch(f"/api/jobs/{job.id}", json={})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Original"

    def test_non_editable_field_ignored(self, client, test_db):
        job = _create_job(test_db, title="Original")
        resp = client.patch(f"/api/jobs/{job.id}", json={
            "title": "Changed",
            "status": "completed",  # not editable -> ignored
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Changed"
        assert data["status"] == "imported"

    def test_invalid_url_returns_422(self, client, test_db):
        job = _create_job(test_db)
        resp = client.patch(f"/api/jobs/{job.id}", json={"url": "not-a-url"})
        assert resp.status_code == 422

    def test_not_found_returns_404(self, client):
        resp = client.patch("/api/jobs/nonexistent-id", json={"title": "X"})
        assert resp.status_code == 404

    def test_notes_and_links_updated(self, client, test_db):
        job = _create_job(test_db, notes="[]", links="[]")
        resp = client.patch(f"/api/jobs/{job.id}", json={
            "notes": [{"title": "Note A", "content": "n1"}],
            "links": [{"title": "Link A", "url": "https://example.com/a"}],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["notes"] == [{"title": "Note A", "content": "n1"}]
        assert data["links"] == [{"title": "Link A", "url": "https://example.com/a"}]

        test_db.refresh(job)
        import json
        assert job.notes == json.dumps([{"title": "Note A", "content": "n1"}], ensure_ascii=False)
        assert job.links == json.dumps([{"title": "Link A", "url": "https://example.com/a"}], ensure_ascii=False)

    def test_notes_and_links_empty_clears(self, client, test_db):
        job = _create_job(test_db, notes='[{"title": "Keep?"}]', links='[{"url": "https://keep.example"}]')
        resp = client.patch(f"/api/jobs/{job.id}", json={"notes": [], "links": []})
        assert resp.status_code == 200
        data = resp.json()
        assert data["notes"] == []
        assert data["links"] == []
        test_db.refresh(job)
        assert json.loads(job.notes) == []
        assert json.loads(job.links) == []

    def test_notes_and_links_existing_preserved_on_other_edit(self, client, test_db):
        job = _create_job(test_db, notes='[{"content": "keep"}]', links='[{"url": "https://keep.example"}]')
        resp = client.patch(f"/api/jobs/{job.id}", json={"title": "Edited"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["notes"] == [{"title": None, "content": "keep"}]
        assert data["links"] == [{"title": None, "url": "https://keep.example"}]

    def test_invalid_link_url_returns_422(self, client, test_db):
        job = _create_job(test_db, links="[]")
        resp = client.patch(f"/api/jobs/{job.id}", json={"links": [{"url": "not-a-url"}]})
        assert resp.status_code == 422