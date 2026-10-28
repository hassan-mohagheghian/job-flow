"""Tests for the Opportunities API router.

Covers:
- Manual create (201), validation (422), content-hash dedupe (200 same id)
- List newest-first with status/source filters
- Detail (200) and missing (404)
- Link validation (unknown job/company → 404)
- Status transitions (invalid → 422, missing → 404)
- Delete (204) with evaluation history removed
- Move to Job (unevaluated → 422, missing → 404)
- Notes / links / base URL at create, user links API, base-url API
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


class TestOpportunityNotesAPI:
    def test_add_and_list_note(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.post(
            f"/api/opportunities/{created['id']}/notes",
            json={"title": "Recruiter replied", "content": "They sent the JD."},
        )
        assert resp.status_code == 201
        note = resp.json()
        assert note["title"] == "Recruiter replied"
        assert note["content"] == "They sent the JD."
        assert note["author"] == "Test User"

        detail = client.get(f"/api/opportunities/{created['id']}").json()
        assert len(detail["notes"]) == 1
        assert detail["notes"][0]["id"] == note["id"]

    def test_add_note_requires_content(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.post(f"/api/opportunities/{created['id']}/notes", json={"content": "  "})
        assert resp.status_code == 422

    def test_add_note_missing_opportunity_404(self, client):
        resp = client.post("/api/opportunities/opp-missing/notes", json={"content": "Hi"})
        assert resp.status_code == 404

    def test_delete_note(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        note = client.post(
            f"/api/opportunities/{created['id']}/notes", json={"content": "Temp"}
        ).json()
        resp = client.delete(f"/api/opportunities/notes/{note['id']}")
        assert resp.status_code == 204
        detail = client.get(f"/api/opportunities/{created['id']}").json()
        assert detail["notes"] == []

    def test_delete_missing_note_404(self, client):
        resp = client.delete("/api/opportunities/notes/note-missing")
        assert resp.status_code == 404


class TestOpportunityDismissAPI:
    def test_dismiss_and_undismiss(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        assert created["dismissed"] is False
        resp = client.put(
            f"/api/opportunities/{created['id']}/dismissed",
            json={"dismissed": True, "note": "Wrong seniority."},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["dismissed"] is True
        assert body["notes"][0]["title"] == "Dismissed"
        assert body["notes"][0]["content"] == "Wrong seniority."

        undismissed = client.put(
            f"/api/opportunities/{created['id']}/dismissed", json={"dismissed": False}
        ).json()
        assert undismissed["dismissed"] is False

    def test_dismiss_missing_404(self, client):
        resp = client.put("/api/opportunities/opp-missing/dismissed", json={"dismissed": True})
        assert resp.status_code == 404

    def test_list_dismissed_filter(self, client):
        first = client.post("/api/opportunities", json=_payload()).json()
        second = client.post(
            "/api/opportunities", json=_payload(raw_content="A different DevOps message.")
        ).json()
        client.put(f"/api/opportunities/{first['id']}/dismissed", json={"dismissed": True})
        only_dismissed = client.get("/api/opportunities", params={"dismissed": "true"}).json()
        assert [i["id"] for i in only_dismissed["items"]] == [first["id"]]
        only_active = client.get("/api/opportunities", params={"dismissed": "false"}).json()
        assert [i["id"] for i in only_active["items"]] == [second["id"]]


class TestOpportunityLinksAndBaseUrlAPI:
    def test_create_with_base_url_notes_and_links(self, client):
        resp = client.post(
            "/api/opportunities",
            json=_payload(
                base_url="https://www.linkedin.com/posts/jane-hiring-123",
                notes=[{"title": "Context", "content": "Came from a LinkedIn post."}],
                links=[{"title": "Company site", "url": "https://acme.example"}],
            ),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["base_url"] == "https://www.linkedin.com/posts/jane-hiring-123"
        assert [n["content"] for n in body["notes"]] == ["Came from a LinkedIn post."]
        assert body["notes"][0]["author"] == "Test User"
        assert [l["url"] for l in body["links"]] == ["https://acme.example"]

    def test_create_rejects_non_http_base_url(self, client):
        resp = client.post("/api/opportunities", json=_payload(base_url="ftp://acme.example"))
        assert resp.status_code == 422

    def test_create_rejects_non_http_link(self, client):
        resp = client.post(
            "/api/opportunities", json=_payload(links=[{"url": "acme.example/careers"}])
        )
        assert resp.status_code == 422

    def test_add_and_delete_link(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.post(
            f"/api/opportunities/{created['id']}/links",
            json={"title": "Recruiter post", "url": "https://www.linkedin.com/posts/jane-123"},
        )
        assert resp.status_code == 201
        link = resp.json()
        assert link["title"] == "Recruiter post"
        assert link["url"] == "https://www.linkedin.com/posts/jane-123"

        detail = client.get(f"/api/opportunities/{created['id']}").json()
        assert len(detail["links"]) == 1
        assert detail["links"][0]["id"] == link["id"]

        deleted = client.delete(f"/api/opportunities/links/{link['id']}")
        assert deleted.status_code == 204
        detail = client.get(f"/api/opportunities/{created['id']}").json()
        assert detail["links"] == []

    def test_add_link_requires_http_url(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.post(
            f"/api/opportunities/{created['id']}/links", json={"url": "acme.example"}
        )
        assert resp.status_code == 422

    def test_add_link_missing_opportunity_404(self, client):
        resp = client.post(
            "/api/opportunities/opp-missing/links", json={"url": "https://acme.example"}
        )
        assert resp.status_code == 404

    def test_delete_missing_link_404(self, client):
        resp = client.delete("/api/opportunities/links/link-missing")
        assert resp.status_code == 404

    def test_patch_base_url(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.patch(
            f"/api/opportunities/{created['id']}/base-url",
            json={"base_url": "https://www.linkedin.com/posts/jane-42"},
        )
        assert resp.status_code == 200
        assert resp.json()["base_url"] == "https://www.linkedin.com/posts/jane-42"

        cleared = client.patch(
            f"/api/opportunities/{created['id']}/base-url", json={"base_url": ""}
        )
        assert cleared.json()["base_url"] is None

    def test_patch_base_url_invalid_422(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.patch(
            f"/api/opportunities/{created['id']}/base-url", json={"base_url": "mailto:jane"}
        )
        assert resp.status_code == 422

    def test_patch_base_url_missing_404(self, client):
        resp = client.patch("/api/opportunities/opp-missing/base-url", json={"base_url": None})
        assert resp.status_code == 404


class TestOpportunityMoveToJobAPI:
    def test_move_requires_evaluated_score_422(self, client):
        created = client.post("/api/opportunities", json=_payload()).json()
        resp = client.post(f"/api/opportunities/{created['id']}/move-to-job")
        assert resp.status_code == 422

    def test_move_missing_opportunity_404(self, client):
        resp = client.post("/api/opportunities/opp-missing/move-to-job")
        assert resp.status_code == 404
