"""Tests for the Skills V2 list API (GET /api/skills/list)."""

from skills.infrastructure.models.skill_model import SkillModel, SkillAliasModel


def _create_skill(sa_session, **kwargs) -> SkillModel:
    defaults = dict(
        name="Python",
        level=1,
        roles="",
        path="",
        category="technical",
        confidence=0.0,
        market_relevance=0.0,
        evidence="[]",
        tags="[]",
        hidden=0,
        source="user",
        source_type="user_input",
        user_id="test-user",
    )
    defaults.update(kwargs)
    model = SkillModel(**defaults)
    sa_session.add(model)
    sa_session.commit()
    sa_session.refresh(model)
    return model


def _create_alias(sa_session, skill_id: int, alias_name: str) -> SkillAliasModel:
    model = SkillAliasModel(
        skill_id=skill_id,
        alias_name=alias_name,
        normalized_name=alias_name.lower(),
    )
    sa_session.add(model)
    sa_session.commit()
    return model


class TestSkillListV2API:
    def test_list_empty(self, client):
        resp = client.get("/api/skills/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total_items"] == 0
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    def test_list_with_skills(self, client, sa_session):
        _create_skill(sa_session, name="Python", level=4)
        _create_skill(sa_session, name="Leadership", category="professional")

        data = client.get("/api/skills/list").json()
        assert len(data["items"]) == 2
        assert data["total_items"] == 2
        names = {i["name"] for i in data["items"]}
        assert names == {"Python", "Leadership"}

    def test_list_excludes_hidden(self, client, sa_session):
        _create_skill(sa_session, name="Python", hidden=0)
        _create_skill(sa_session, name="jQuery", hidden=1)

        data = client.get("/api/skills/list").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "Python"

    def test_pagination_cursor(self, client, sa_session):
        for i in range(5):
            _create_skill(sa_session, name=f"Skill {i}")

        data = client.get("/api/skills/list?page_size=2").json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"]

        data2 = client.get(f"/api/skills/list?page_size=2&cursor={data['next_cursor']}").json()
        assert len(data2["items"]) == 2
        assert data2["has_more"] is True

        data3 = client.get(f"/api/skills/list?page_size=2&cursor={data2['next_cursor']}").json()
        assert len(data3["items"]) == 1
        assert data3["has_more"] is False
        assert data3["next_cursor"] is None

    def test_pagination_total_constant(self, client, sa_session):
        for i in range(4):
            _create_skill(sa_session, name=f"Skill {i}")
        data = client.get("/api/skills/list?page_size=2").json()
        data2 = client.get(f"/api/skills/list?page_size=2&cursor={data['next_cursor']}").json()
        assert data["total_items"] == 4
        assert data2["total_items"] == 4

    def test_search_by_name(self, client, sa_session):
        _create_skill(sa_session, name="PostgreSQL", category="technical")
        _create_skill(sa_session, name="React", category="engineering")

        data = client.get("/api/skills/list?query=postgres").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "PostgreSQL"

    def test_search_by_roles(self, client, sa_session):
        _create_skill(sa_session, name="Kafka", roles="backend engineer data")
        _create_skill(sa_session, name="Docker", roles="devops")

        data = client.get("/api/skills/list?query=backend").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "Kafka"

    def test_search_by_alias(self, client, sa_session):
        skill = _create_skill(sa_session, name="React", category="engineering")
        _create_alias(sa_session, skill.id, "ReactJS")

        data = client.get("/api/skills/list?query=reactjs").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "React"

    def test_category_filter(self, client, sa_session):
        _create_skill(sa_session, name="Python", category="technical")
        _create_skill(sa_session, name="Leadership", category="professional")

        data = client.get("/api/skills/list?category=professional").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "Leadership"

    def test_multi_category_filter_or_semantics(self, client, sa_session):
        from skills.infrastructure import SQLAlchemySkillRepository

        repo = SQLAlchemySkillRepository(sa_session, user_id="test-user")
        python = _create_skill(sa_session, name="Python", category="")
        docker = _create_skill(sa_session, name="Docker", category="")
        leadership = _create_skill(sa_session, name="Leadership", category="")
        repo.set_categories(python.id, ["technical", "engineering"])
        repo.set_categories(docker.id, ["infrastructure"])
        repo.set_categories(leadership.id, ["professional"])

        data = client.get("/api/skills/list?categories=technical&categories=professional").json()
        names = {i["name"] for i in data["items"]}
        assert names == {"Python", "Leadership"}

    def test_multi_category_filter_matches_any_category(self, client, sa_session):
        from skills.infrastructure import SQLAlchemySkillRepository

        repo = SQLAlchemySkillRepository(sa_session, user_id="test-user")
        fullstack = _create_skill(sa_session, name="Fullstack", category="")
        repo.set_categories(fullstack.id, ["technical", "domain"])

        data = client.get("/api/skills/list?categories=domain").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "Fullstack"

    def test_multi_category_filter_empty_is_no_filter(self, client, sa_session):
        _create_skill(sa_session, name="Python", category="technical")
        _create_skill(sa_session, name="Leadership", category="professional")

        data = client.get("/api/skills/list?categories=").json()
        assert data["total_items"] == 2

    def test_multi_category_filter_legacy_category_still_works(self, client, sa_session):
        _create_skill(sa_session, name="Python", category="technical")
        _create_skill(sa_session, name="Leadership", category="professional")

        data = client.get("/api/skills/list?category=technical").json()
        assert data["total_items"] == 1
        assert data["items"][0]["name"] == "Python"

    def test_sort_by_level(self, client, sa_session):
        _create_skill(sa_session, name="Kafka", level=1)
        _create_skill(sa_session, name="Python", level=4)
        _create_skill(sa_session, name="React", level=2)

        data = client.get("/api/skills/list?sort=level&order=desc").json()
        names = [i["name"] for i in data["items"]]
        assert names == ["Python", "React", "Kafka"]

        data = client.get("/api/skills/list?sort=level&order=asc").json()
        names = [i["name"] for i in data["items"]]
        assert names == ["Kafka", "React", "Python"]

    def test_sort_by_market_relevance_nulls_last(self, client, sa_session):
        _create_skill(sa_session, name="No Demand", market_relevance=0)
        _create_skill(sa_session, name="High Demand", market_relevance=9.0)

        data = client.get("/api/skills/list?sort=market_relevance&order=desc").json()
        names = [i["name"] for i in data["items"]]
        assert names == ["High Demand", "No Demand"]

    def test_sort_by_mention_count(self, client, sa_session):
        from skills.infrastructure import SQLAlchemySkillRepository

        python = _create_skill(sa_session, name="Python")
        k8s = _create_skill(sa_session, name="Kubernetes")
        go = _create_skill(sa_session, name="Go")
        repo = SQLAlchemySkillRepository(sa_session, user_id="test-user")
        repo.upsert_mentions(python.id, "job", "job-1")
        repo.upsert_mentions(python.id, "job", "job-2")
        repo.upsert_mentions(python.id, "company", "company-1")
        repo.upsert_mentions(k8s.id, "job", "job-3")

        data = client.get("/api/skills/list?sort=mention_count&order=desc").json()
        names = [i["name"] for i in data["items"]]
        assert names == ["Python", "Kubernetes", "Go"]

        data = client.get("/api/skills/list?sort=mention_count&order=asc").json()
        names = [i["name"] for i in data["items"]]
        assert names == ["Go", "Kubernetes", "Python"]

    def test_default_sort_by_created_at(self, client, sa_session):
        from skills.infrastructure import SQLAlchemySkillRepository

        low = _create_skill(sa_session, name="Low")
        high = _create_skill(sa_session, name="High")
        repo = SQLAlchemySkillRepository(sa_session, user_id="test-user")
        repo.upsert_mentions(high.id, "job", "job-1")
        repo.upsert_mentions(high.id, "job", "job-2")
        repo.upsert_mentions(low.id, "job", "job-3")

        # Default list order is newest first (created_at desc), regardless of mentions.
        data = client.get("/api/skills/list").json()
        names = [i["name"] for i in data["items"]]
        assert names == ["High", "Low"]

    def test_item_shape(self, client, sa_session):
        skill = _create_skill(
            sa_session,
            name="Python",
            level=4,
            roles="backend",
            path="engineer",
            category="technical",
            confidence=0.9,
            market_relevance=8.5,
            evidence="[]",
            tags='["ai", "ml"]',
        )
        _create_alias(sa_session, skill.id, "CPython")

        item = client.get("/api/skills/list").json()["items"][0]
        assert item["id"] == skill.id
        assert item["name"] == "Python"
        assert item["level"] == 4
        assert item["roles"] == "backend"
        assert item["path"] == "engineer"
        assert item["category"] == "technical"
        assert item["confidence"] == 0.9
        assert item["market_relevance"] == 8.5
        assert item["tags"] == ["ai", "ml"]
        assert item["aliases"] == ["CPython"]
        assert item["source_type"] == "user_input"
        assert item["mention_count"] == 0
        assert item["created_at"] is not None

    def test_item_shape_ai_generated_source(self, client, sa_session):
        _create_skill(sa_session, name="Kubernetes", source_type="ai_generated")

        item = client.get("/api/skills/list").json()["items"][0]
        assert item["source_type"] == "ai_generated"

    def test_get_by_id(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python", level=4, category="technical")
        _create_alias(sa_session, skill.id, "CPython")

        resp = client.get(f"/api/skills/{skill.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == skill.id
        assert data["name"] == "Python"
        assert data["level"] == 4
        assert data["aliases"] == ["CPython"]
        assert data["tags"] == []
        assert data["source_type"] == "user_input"

    def test_get_by_id_not_found(self, client):
        resp = client.get("/api/skills/9999")
        assert resp.status_code == 404

    def test_get_by_id_literal_routes_still_win(self, client, sa_session):
        _create_skill(sa_session, name="Python")
        resp = client.get("/api/skills/list")
        assert resp.status_code == 200
        assert "items" in resp.json()


def test_list_mention_count(client, sa_session):
    from skills.infrastructure import SQLAlchemySkillRepository

    python = _create_skill(sa_session, name="Python")
    k8s = _create_skill(sa_session, name="Kubernetes")
    repo = SQLAlchemySkillRepository(sa_session, user_id="test-user")
    repo.upsert_mentions(python.id, "job", "job-1", status="", evidence="[]")
    repo.upsert_mentions(python.id, "company", "company-1", status="", evidence="[]")
    repo.upsert_mentions(k8s.id, "job", "job-2", status="", evidence="[]")

    items = client.get("/api/skills/list").json()["items"]
    by_name = {i["name"]: i["mention_count"] for i in items}
    assert by_name == {"Python": 2, "Kubernetes": 1}


def test_list_mention_count_folds_aliases(client, sa_session):
    from skills.infrastructure import SQLAlchemySkillRepository

    kubernetes = _create_skill(sa_session, name="Kubernetes")
    k8s = _create_skill(sa_session, name="K8s")
    _create_alias(sa_session, kubernetes.id, "K8s")
    repo = SQLAlchemySkillRepository(sa_session, user_id="test-user")
    repo.upsert_mentions(kubernetes.id, "job", "job-1")
    repo.upsert_mentions(k8s.id, "job", "job-2")
    repo.upsert_mentions(k8s.id, "company", "company-1")

    items = client.get("/api/skills/list").json()["items"]
    by_name = {i["name"]: i["mention_count"] for i in items}
    assert by_name["Kubernetes"] == 3
    assert by_name["K8s"] == 2


def test_list_sort_by_mention_count_folds_aliases(client, sa_session):
    from skills.infrastructure import SQLAlchemySkillRepository

    kubernetes = _create_skill(sa_session, name="Kubernetes")
    k8s = _create_skill(sa_session, name="K8s")
    go = _create_skill(sa_session, name="Go")
    _create_alias(sa_session, kubernetes.id, "K8s")
    repo = SQLAlchemySkillRepository(sa_session, user_id="test-user")
    repo.upsert_mentions(kubernetes.id, "job", "job-1")
    repo.upsert_mentions(k8s.id, "job", "job-2")
    repo.upsert_mentions(k8s.id, "company", "company-1")
    repo.upsert_mentions(go.id, "job", "job-3")

    data = client.get("/api/skills/list?sort=mention_count&order=desc").json()
    names = [i["name"] for i in data["items"]]
    assert names == ["Kubernetes", "K8s", "Go"]


def test_add_alias_api(client, sa_session):
    skill = _create_skill(sa_session, name="React")
    resp = client.post(f"/api/skills/{skill.id}/aliases", json={"alias_name": "ReactJS"})
    assert resp.status_code == 200
    assert "ReactJS" in resp.json()["aliases"]

    items = client.get("/api/skills/list").json()["items"]
    assert items[0]["aliases"] == ["ReactJS"]


def test_remove_alias_api(client, sa_session):
    skill = _create_skill(sa_session, name="React")
    _create_alias(sa_session, skill.id, "ReactJS")
    resp = client.delete(f"/api/skills/{skill.id}/aliases", params={"alias_name": "ReactJS"})
    assert resp.status_code == 200
    assert "ReactJS" not in resp.json()["aliases"]


def test_remove_alias_with_slash_in_name_api(client, sa_session):
    skill = _create_skill(sa_session, name="AI")
    _create_alias(sa_session, skill.id, "AI / NLP")
    resp = client.delete(f"/api/skills/{skill.id}/aliases", params={"alias_name": "AI / NLP"})
    assert resp.status_code == 200
    assert "AI / NLP" not in resp.json()["aliases"]


def test_add_alias_missing_skill_404(client, sa_session):
    resp = client.post("/api/skills/9999/aliases", json={"alias_name": "X"})
    assert resp.status_code == 404


def test_merge_folds_mentions_via_api(client, sa_session):
    from skills.infrastructure import SQLAlchemySkillRepository

    target = _create_skill(sa_session, name="React")
    source = _create_skill(sa_session, name="ReactJS")
    repo = SQLAlchemySkillRepository(sa_session, user_id="test-user")
    repo.upsert_mentions(source.id, "job", "job-1")

    resp = client.post("/api/skills/merge", json={"target_id": target.id, "source_ids": [source.id]})
    assert resp.status_code == 200
    assert resp.json()["status"] == "merged"

    items = client.get("/api/skills/list").json()["items"]
    by_name = {i["name"]: i for i in items}
    assert by_name["React"]["mention_count"] == 1


def test_merge_rejects_empty_sources(client, sa_session):
    target = _create_skill(sa_session, name="React")
    resp = client.post("/api/skills/merge", json={"target_id": target.id, "source_ids": []})
    assert resp.status_code == 400


def test_merge_rejects_target_in_sources(client, sa_session):
    target = _create_skill(sa_session, name="React")
    resp = client.post("/api/skills/merge", json={"target_id": target.id, "source_ids": [target.id]})
    assert resp.status_code == 400


class TestSkillNotesAndLinks:
    def test_add_note(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        resp = client.post(f"/api/skills/{skill.id}/notes", json={"content": "Started learning decorators"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Started learning decorators"
        assert data["skill_id"] == skill.id

    def test_add_note_empty_content_rejected(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        resp = client.post(f"/api/skills/{skill.id}/notes", json={"content": "   "})
        assert resp.status_code == 422

    def test_add_note_missing_skill_404(self, client, sa_session):
        resp = client.post("/api/skills/99999/notes", json={"content": "test"})
        assert resp.status_code == 404

    def test_delete_note(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        created = client.post(f"/api/skills/{skill.id}/notes", json={"content": "test note"}).json()
        resp = client.delete(f"/api/skills/notes/{created['id']}")
        assert resp.status_code == 204

    def test_delete_note_missing_404(self, client, sa_session):
        resp = client.delete("/api/skills/notes/99999")
        assert resp.status_code == 404

    def test_get_skill_includes_notes(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        client.post(f"/api/skills/{skill.id}/notes", json={"content": "note one"})
        client.post(f"/api/skills/{skill.id}/notes", json={"content": "note two"})
        detail = client.get(f"/api/skills/{skill.id}").json()
        assert len(detail["notes"]) == 2
        contents = [n["content"] for n in detail["notes"]]
        assert "note one" in contents
        assert "note two" in contents

    def test_add_link(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        resp = client.post(f"/api/skills/{skill.id}/links", json={"title": "Docs", "url": "https://docs.python.org"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Docs"
        assert data["url"] == "https://docs.python.org"
        assert data["skill_id"] == skill.id

    def test_add_link_empty_title_rejected(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        resp = client.post(f"/api/skills/{skill.id}/links", json={"title": "", "url": "https://example.com"})
        assert resp.status_code == 422

    def test_add_link_empty_url_rejected(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        resp = client.post(f"/api/skills/{skill.id}/links", json={"title": "Docs", "url": ""})
        assert resp.status_code == 422

    def test_add_link_missing_skill_404(self, client, sa_session):
        resp = client.post("/api/skills/99999/links", json={"title": "Docs", "url": "https://example.com"})
        assert resp.status_code == 404

    def test_delete_link(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        created = client.post(f"/api/skills/{skill.id}/links", json={"title": "Docs", "url": "https://example.com"}).json()
        resp = client.delete(f"/api/skills/links/{created['id']}")
        assert resp.status_code == 204

    def test_delete_link_missing_404(self, client, sa_session):
        resp = client.delete("/api/skills/links/99999")
        assert resp.status_code == 404

    def test_get_skill_includes_links(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        client.post(f"/api/skills/{skill.id}/links", json={"title": "Docs", "url": "https://docs.python.org"})
        client.post(f"/api/skills/{skill.id}/links", json={"title": "Tutorial", "url": "https://tutorial.python.org"})
        detail = client.get(f"/api/skills/{skill.id}").json()
        assert len(detail["links"]) == 2
        titles = [l["title"] for l in detail["links"]]
        assert "Docs" in titles
        assert "Tutorial" in titles

    def test_notes_newest_first(self, client, sa_session):
        skill = _create_skill(sa_session, name="Python")
        client.post(f"/api/skills/{skill.id}/notes", json={"content": "first"})
        client.post(f"/api/skills/{skill.id}/notes", json={"content": "second"})
        detail = client.get(f"/api/skills/{skill.id}").json()
        assert detail["notes"][0]["content"] == "second"
        assert detail["notes"][1]["content"] == "first"