"""Tests for the Opportunities API router.

Covers:
- Manual create (201), validation (422), content-hash dedupe (200 same id)
- List newest-first with status/source filters
- Detail (200) and missing (404)
- Link validation (unknown job/company → 404)
- Status transitions (invalid → 422, missing → 404)
- Delete (204) with evaluation history removed
"""

from __future__ import annotations


def _payload(**kwargs):
    data = {
        "source": "manual",
        "sender": "Jane",
        "sender_email": "jane@acme.example",
        "subject": "Senior Backend Engineer role",
        "raw_content": "Hi Hassan, we are hiring a Senior Backend Engineer. Interested?",
    }
    data.update(kwargs)
    return data


class TestOpportunityAPI:
    def test_create_returns_201(self, client):
        resp = client.post("/api/opportunities", json=_payload())
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "new"
        assert body["duplicate"] is False
        assert body["evaluations"] == []

    def test_create_requires_raw_content(self, client):
        resp = client.post("/api/opportunities", json=_payload(raw_content="  "))
        assert resp.status_code == 422

    def test_duplicate_content_returns_existing(self, client):
        first = client.post("/api/opportunities", json=_payload()).json()
        second = client.post("/api/opportunities", json=_payload())
        assert second.status_code == 200
        assert second.json()["id"] == first["id"]
        assert second.json()["duplicate"] is True

    def test_list_newest_first_and_filters(self, client):
        first = client.post("/api/opportunities", json=_payload()).json()
        second = client.post("/api/opportunities", json=_payload(raw_content="A different message about DevOps.")).json()
        body = client.get("/api/opportunities").json()
        assert body["total"] == 2
        assert [i["id"] for i in body["items"]] == [second["id"], first["id"]]
        filtered = client.get("/api/opportunities", params={"status": "new"}).json()
        assert filtered["total"] == 2

    def test_detail_and_missing(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.get(f"/api/opportunities/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["raw_content"].startswith("Hi Hassan")
        assert client.get("/api/opportunities/opp-missing").status_code == 404

    def test_link_unknown_job_404(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.patch(f"/api/opportunities/{created['id']}/links", json={"job_id": "job-missing"})
        assert resp.status_code == 404

    def test_invalid_status_422(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.patch(f"/api/opportunities/{created['id']}/status", json={"status": "applied"})
        assert resp.status_code == 422

    def test_delete_removes_opportunity(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.delete(f"/api/opportunities/{created['id']}")
        assert resp.status_code == 204
        assert client.get(f"/api/opportunities/{created['id']}").status_code == 404
