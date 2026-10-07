"""SQLAlchemy implementation of the opportunity repositories."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from sqlalchemy.orm import Session

from opportunities.domain.repositories.opportunity_repository import (
    IOpportunityEvaluationRepository,
    IOpportunityRepository,
)
from opportunities.infrastructure.mappers import (
    dump_json_fields,
    evaluation_model_to_dict,
    opportunity_model_to_dict,
)
from opportunities.infrastructure.models.opportunity_model import (
    OpportunityEvaluationModel,
    OpportunityModel,
)


class SQLAlchemyOpportunityRepository(IOpportunityRepository):
    """SQLAlchemy implementation of the opportunity repository."""

    def __init__(self, session: Session, user_id: str = ""):
        self._session = session
        self._user_id = user_id

    def _scoped(self, query):
        if self._user_id:
            return query.filter(OpportunityModel.user_id == self._user_id)
        return query

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = dump_json_fields(data)
        if self._user_id and not payload.get("user_id"):
            payload["user_id"] = self._user_id
        model = OpportunityModel(
            **{k: v for k, v in payload.items() if hasattr(OpportunityModel, k)}
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return opportunity_model_to_dict(model)

    def get_by_id(self, opportunity_id: str) -> dict[str, Any] | None:
        q = self._session.query(OpportunityModel).filter(OpportunityModel.id == opportunity_id)
        model = self._scoped(q).first()
        return opportunity_model_to_dict(model) if model else None

    def get_by_content_hash(self, content_hash: str) -> dict[str, Any] | None:
        q = self._session.query(OpportunityModel).filter(
            OpportunityModel.content_hash == content_hash
        )
        model = self._scoped(q).first()
        return opportunity_model_to_dict(model) if model else None

    def get_by_source_message(self, source: str, source_message_id: str) -> dict[str, Any] | None:
        q = self._session.query(OpportunityModel).filter(
            OpportunityModel.source == source,
            OpportunityModel.source_message_id == source_message_id,
        )
        model = self._scoped(q).first()
        return opportunity_model_to_dict(model) if model else None

    def list(
        self,
        status: str | None = None,
        source: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        q = self._session.query(OpportunityModel)
        q = self._scoped(q)
        if status:
            q = q.filter(OpportunityModel.status == status)
        if source:
            q = q.filter(OpportunityModel.source == source)
        if query:
            like = f"%{query}%"
            q = q.filter(
                (OpportunityModel.raw_content.ilike(like))
                | (OpportunityModel.subject.ilike(like))
                | (OpportunityModel.sender.ilike(like))
                | (OpportunityModel.company_name.ilike(like))
                | (OpportunityModel.job_title.ilike(like))
            )
        total = q.count()
        rows = (
            q.order_by(OpportunityModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [opportunity_model_to_dict(r) for r in rows], total

    def update(self, opportunity_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        model = self._session.query(OpportunityModel).filter(
            OpportunityModel.id == opportunity_id
        ).first()
        if not model:
            return None
        payload = dump_json_fields(data)
        for key, value in payload.items():
            if hasattr(OpportunityModel, key) and key != "id":
                setattr(model, key, value)
        model.updated_at = datetime.now(UTC).isoformat()
        self._session.commit()
        self._session.refresh(model)
        return self.get_by_id(opportunity_id)

    def delete(self, opportunity_id: str) -> bool:
        self._session.query(OpportunityEvaluationModel).filter(
            OpportunityEvaluationModel.opportunity_id == opportunity_id
        ).delete()
        deleted = (
            self._session.query(OpportunityModel)
            .filter(OpportunityModel.id == opportunity_id)
            .delete()
        )
        self._session.commit()
        return bool(deleted)


class SQLAlchemyOpportunityEvaluationRepository(IOpportunityEvaluationRepository):
    """SQLAlchemy implementation of the evaluation snapshot repository."""

    def __init__(self, session: Session):
        self._session = session

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        import json

        payload = dict(data)
        snapshot = payload.get("snapshot")
        if snapshot is not None and not isinstance(snapshot, str):
            payload["snapshot"] = json.dumps(snapshot, ensure_ascii=False)
        model = OpportunityEvaluationModel(
            **{k: v for k, v in payload.items() if hasattr(OpportunityEvaluationModel, k)}
        )
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return evaluation_model_to_dict(model)

    def list_for_opportunity(self, opportunity_id: str) -> list[dict[str, Any]]:
        rows = (
            self._session.query(OpportunityEvaluationModel)
            .filter(OpportunityEvaluationModel.opportunity_id == opportunity_id)
            .order_by(OpportunityEvaluationModel.created_at.desc())
            .all()
        )
        return [evaluation_model_to_dict(r) for r in rows]
