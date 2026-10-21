"""SQLAlchemy implementation of the application repository."""

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from applications.domain.entities.application import ApplicationStatus
from applications.domain.repositories.application_repository import IApplicationRepository
from applications.infrastructure.mappers import (
    application_model_to_dict,
    dict_to_application_model,
)
from applications.infrastructure.models.application_model import (
    ApplicationDocumentModel,
    ApplicationFollowUpModel,
    ApplicationModel,
    ApplicationStatusEventModel,
)


class SQLAlchemyApplicationRepository(IApplicationRepository):
    """SQLAlchemy implementation of the application repository."""

    def __init__(self, session: Session, user_id: str = ""):
        self._session = session
        self._user_id = user_id

    def get_by_id(self, application_id: str) -> dict[str, Any] | None:
        q = self._session.query(ApplicationModel).filter(
            ApplicationModel.id == application_id
        )
        if self._user_id:
            q = q.filter(ApplicationModel.user_id == self._user_id)
        model = q.first()
        return application_model_to_dict(model) if model else None

    def get_by_job_id(self, job_id: str) -> dict[str, Any] | None:
        q = self._session.query(ApplicationModel).filter(
            ApplicationModel.job_id == job_id
        )
        if self._user_id:
            q = q.filter(ApplicationModel.user_id == self._user_id)
        model = q.first()
        return application_model_to_dict(model) if model else None

    def list_ids_by_job(self, job_id: str) -> list[str]:
        q = self._session.query(ApplicationModel.id).filter(
            ApplicationModel.job_id == job_id
        )
        if self._user_id:
            q = q.filter(ApplicationModel.user_id == self._user_id)
        return [row[0] for row in q.all()]

    def statuses_by_job_ids(self, job_ids: list[str]) -> dict[str, str]:
        if not job_ids:
            return {}
        q = self._session.query(ApplicationModel.job_id, ApplicationModel.status).filter(
            ApplicationModel.job_id.in_(job_ids)
        )
        if self._user_id:
            q = q.filter(ApplicationModel.user_id == self._user_id)
        rows = q.all()
        return {job_id: status for job_id, status in rows}

    def job_ids_with_application(self) -> list[str]:
        q = self._session.query(ApplicationModel.job_id).distinct()
        if self._user_id:
            q = q.filter(ApplicationModel.user_id == self._user_id)
        return [row[0] for row in q.all()]

    def status_distribution(self) -> dict[str, Any]:
        q = self._session.query(
            ApplicationModel.status, func.count(ApplicationModel.id)
        )
        if self._user_id:
            q = q.filter(ApplicationModel.user_id == self._user_id)
        counts = {
            str(status): int(count)
            for status, count in q.group_by(ApplicationModel.status).all()
            if status is not None
        }

        known = [status for status in ApplicationStatus.ALL if counts.get(status)]
        unknown = sorted(status for status in counts if status not in ApplicationStatus.ALL)
        return {
            "items": [
                {"status": status, "count": counts[status]}
                for status in (*known, *unknown)
                if counts[status] > 0
            ],
            "total": sum(counts.values()),
        }

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        data.setdefault("user_id", self._user_id)
        model = dict_to_application_model(data)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return application_model_to_dict(model)

    def update(self, application_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        model = (
            self._session.query(ApplicationModel)
            .filter(ApplicationModel.id == application_id)
            .first()
        )
        if not model:
            return None
        for field in ("status", "applied_at", "updated_at"):
            if field in data:
                setattr(model, field, data[field])
        self._session.commit()
        return application_model_to_dict(model)

    def delete_by_job(self, job_id: str) -> int:
        app_ids = self.list_ids_by_job(job_id)
        if not app_ids:
            return 0
        for child_model in (ApplicationFollowUpModel, ApplicationDocumentModel, ApplicationStatusEventModel):
            self._session.query(child_model).filter(
                child_model.application_id.in_(app_ids)
            ).delete(synchronize_session=False)
        deleted = self._session.query(ApplicationModel).filter(
            ApplicationModel.job_id == job_id
        ).delete(synchronize_session=False)
        self._session.commit()
        return int(deleted)
