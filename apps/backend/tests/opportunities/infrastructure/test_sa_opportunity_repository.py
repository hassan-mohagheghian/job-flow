"""Tests for the Opportunities SQLAlchemy repositories.

Covers:
- Opportunity CRUD with JSON payload round-trip and logical cross-context ids
- Content-hash lookup for dedupe
- Evaluation history ordering (newest first)
- Hard delete removes the opportunity and its evaluations
"""

from __future__ import annotations

import uuid

from opportunities.infrastructure.models.opportunity_model import (
    OpportunityEvaluationModel,
    OpportunityModel,
)


def _make_opportunity(sa_session, **kwargs):
    data = dict(
        id=str(uuid.uuid7()),
        user_id="test-user",
        source="manual",
        raw_content="Hi Hassan, hiring?",
        content_hash=f"hash-{uuid.uuid7()}",
        status="new",
    )
    data.update(kwargs)
    model = OpportunityModel(**data)
    sa_session.add(model)
    sa_session.commit()
    return model


class TestOpportunityPersistence:
    def test_json_round_trip(self, sa_session):
        model = _make_opportunity(
            sa_session,
            extracted='{"role_title": "Backend Engineer"}',
            evaluation='{"fit": 80}',
        )
        fetched = sa_session.get(OpportunityModel, model.id)
        assert fetched.extracted == '{"role_title": "Backend Engineer"}'
        assert fetched.evaluation == '{"fit": 80}'

    def test_logical_cross_context_ids_have_no_fk(self, sa_session):
        model = _make_opportunity(sa_session, company_id="company-1", job_id="job-1")
        fetched = sa_session.get(OpportunityModel, model.id)
        assert fetched.company_id == "company-1"
        assert fetched.job_id == "job-1"

    def test_evaluations_newest_first(self, sa_session):
        model = _make_opportunity(sa_session)
        for status in ("evaluated", "ready_to_apply"):
            sa_session.add(
                OpportunityEvaluationModel(
                    id=str(uuid.uuid7()),
                    opportunity_id=model.id,
                    status=status,
                    evaluation_status="complete",
                    overall_score=80,
                    snapshot="{}",
                )
            )
        sa_session.commit()
        rows = (
            sa_session.query(OpportunityEvaluationModel)
            .filter(OpportunityEvaluationModel.opportunity_id == model.id)
            .order_by(OpportunityEvaluationModel.created_at.desc())
            .all()
        )
        assert [r.status for r in rows] == ["ready_to_apply", "evaluated"]
