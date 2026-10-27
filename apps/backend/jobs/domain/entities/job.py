"""Job entity — aggregate root for the Jobs bounded context.

Represents a job posting with all its attributes.
Preserves existing `num` (int) primary key from the database.
"""

from __future__ import annotations

from datetime import datetime, UTC
from typing import Any

from shared.domain.entity import BaseEntity


class Job(BaseEntity):
    """Job aggregate root.

    A Job represents a job posting in the system. It is the primary entity
    of the Jobs bounded context and owns its data.

    Note: Uses `num` (int) as the primary key, inherited from the existing
    database schema. The BaseEntity `id` property maps to `num`.
    """

    def __init__(
        self,
        id: str,
        company: str | None = None,
        role: str | None = None,
        location: str | None = None,
        salary: str | None = None,
        stack: str | None = None,
        visa: str | None = None,
        applicants: str | None = None,
        posted: str | None = None,
        industry: str | None = None,
        domain: str | None = None,
        notes: str | None = None,
        action: str | None = None,
        url: str | None = None,
        workflow_log: str = "[]",
        deleted: int = 0,
        work_types: list[str] | None = None,
        employment_types: list[str] | None = None,
        raw_description: str | None = None,
        structured_description: str | None = None,
        adv_at: str | None = None,
        see_at: str | None = None,
        apply_reason: str | None = None,
        fit_score: int | None = None,
        success_score: int | None = None,
        overall_score: int | None = None,
        company_id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        title: str | None = None,
        description: str | None = None,
        apply_time: str | None = None,
        response_time: str | None = None,
        response_status: str | None = None,
        rescoring: int = 0,
        pinned: int = 0,
        status: str = "imported",
        queue_order: int = 0,
        current_node: str | None = None,
        progress_pct: float = 0,
        error: str | None = None,
        retry_count: int = 0,
        failure_reason: str | None = None,
        failure_step: str | None = None,
        failure_timestamp: str | None = None,
        session_id: str | None = None,
        easy_apply: int | None = None,
    ):
        # Use id as the identity (UUID from new schema)
        super().__init__(id=id, created_at=created_at, updated_at=updated_at)
        self.company = company
        self.role = role
        self.location = location
        self.salary = salary
        self.stack = stack
        self.visa = visa
        self.applicants = applicants
        self.posted = posted
        self.industry = industry
        self.domain = domain
        self.notes = notes
        self.action = action
        self.url = url
        self.workflow_log = workflow_log
        self.deleted = deleted
        self.work_types = work_types or []
        self.employment_types = employment_types or ["Full-time"]
        self.raw_description = raw_description
        self.structured_description = structured_description
        self.adv_at = adv_at
        self.see_at = see_at
        self.apply_reason = apply_reason
        self.fit_score = fit_score
        self.success_score = success_score
        self.overall_score = overall_score
        self.company_id = company_id
        self.title = title
        self.description = description
        self.apply_time = apply_time
        self.response_time = response_time
        self.response_status = response_status
        self.rescoring = rescoring
        self.pinned = pinned
        self.status = status
        self.queue_order = queue_order
        self.current_node = current_node
        self.progress_pct = progress_pct
        self.error = error
        self.retry_count = retry_count
        self.failure_reason = failure_reason
        self.failure_step = failure_step
        self.failure_timestamp = failure_timestamp
        self.session_id = session_id
        self.easy_apply = easy_apply

    def is_deleted(self) -> bool:
        return self.deleted == 1

    def mark_deleted(self) -> None:
        self.deleted = 1
        self.updated_at = datetime.now(UTC)

    def is_rescoring(self) -> bool:
        return self.rescoring == 1

    def set_rescoring(self, value: bool) -> None:
        self.rescoring = 1 if value else 0
        self.updated_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert entity to dictionary for persistence."""
        return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "location": self.location,
            "salary": self.salary,
            "stack": self.stack,
            "visa": self.visa,
            "applicants": self.applicants,
            "posted": self.posted,
            "industry": self.industry,
            "domain": self.domain,
            "notes": self.notes,
            "action": self.action,
            "url": self.url,
            "workflow_log": self.workflow_log,
            "deleted": self.deleted,
            "work_types": self.work_types,
            "employment_types": self.employment_types,
            "raw_description": self.raw_description,
            "structured_description": self.structured_description,
            "adv_at": self.adv_at,
            "see_at": self.see_at,
            "apply_reason": self.apply_reason,
            "fit_score": self.fit_score,
            "success_score": self.success_score,
            "overall_score": self.overall_score,
            "company_id": self.company_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "title": self.title,
            "description": self.description,
            "apply_time": self.apply_time,
            "response_time": self.response_time,
            "response_status": self.response_status,
            "rescoring": self.rescoring,
            "pinned": self.pinned,
            "status": self.status,
            "queue_order": self.queue_order,
            "current_node": self.current_node,
            "progress_pct": self.progress_pct,
            "error": self.error,
            "retry_count": self.retry_count,
            "failure_reason": self.failure_reason,
            "failure_step": self.failure_step,
            "failure_timestamp": self.failure_timestamp,
            "session_id": self.session_id,
            "easy_apply": self.easy_apply,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        """Create a Job entity from a dictionary (e.g., from DB row)."""
        return cls(
            id=data["id"],
            company=data.get("company"),
            role=data.get("role"),
            location=data.get("location"),
            salary=data.get("salary"),
            stack=data.get("stack"),
            visa=data.get("visa"),
            applicants=data.get("applicants"),
            posted=data.get("posted"),
            industry=data.get("industry"),
            domain=data.get("domain"),
            notes=data.get("notes"),
            action=data.get("action"),
            url=data.get("url"),
            workflow_log=data.get("workflow_log", "[]"),
            deleted=data.get("deleted", 0),
            work_types=data.get("work_types") or [],
            employment_types=data.get("employment_types") or ["Full-time"],
            raw_description=data.get("raw_description"),
            structured_description=data.get("structured_description"),
            adv_at=data.get("adv_at"),
            see_at=data.get("see_at"),
            apply_reason=data.get("apply_reason"),
            fit_score=data.get("fit_score"),
            success_score=data.get("success_score"),
            overall_score=data.get("overall_score"),
            company_id=data.get("company_id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            title=data.get("title"),
            description=data.get("description"),
            apply_time=data.get("apply_time"),
            response_time=data.get("response_time"),
            response_status=data.get("response_status"),
            rescoring=data.get("rescoring", 0),
            pinned=data.get("pinned", 0),
            status=data.get("status", "imported"),
            queue_order=data.get("queue_order", 0),
            current_node=data.get("current_node"),
            progress_pct=data.get("progress_pct", 0),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            failure_reason=data.get("failure_reason"),
            failure_step=data.get("failure_step"),
            failure_timestamp=data.get("failure_timestamp"),
            session_id=data.get("session_id"),
            easy_apply=data.get("easy_apply"),
        )
