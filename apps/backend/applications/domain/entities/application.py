"""Application aggregate entities.

The Application is the aggregate root of the Applications bounded context. It
represents a user's application for a single job and owns its follow-ups and
versioned documents (tailored resume / cover letter).

Cross-context references (``job_id``) are logical references only — there is no
FK into the ``job`` schema (AGENTS.md rule 15).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
import uuid


@dataclass
class TimestampedEntity:
    """Minimal timestamped entity base used by the Applications context."""

    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class ApplicationStatus:
    """Allowed application statuses (application funnel for job tracking).

    ``seen`` is the mandatory initial state: it is auto-recorded as the first
    timeline node when the application is created, cannot be deleted, and is not
    user-selectable. The actionable funnel is seen → preparing →
    ready_to_apply → applied → interview → offer → accepted, with rejected /
    withdrawn / expired as terminal states (expired is posting-side: the job
    is no longer accepting applications).
    """

    SEEN = "seen"
    PREPARING = "preparing"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"

    ALL = (
        SEEN,
        PREPARING,
        READY_TO_APPLY,
        APPLIED,
        INTERVIEW,
        OFFER,
        ACCEPTED,
        REJECTED,
        WITHDRAWN,
        EXPIRED,
    )

    SELECTABLE = (
        PREPARING,
        READY_TO_APPLY,
        APPLIED,
        INTERVIEW,
        OFFER,
        ACCEPTED,
        REJECTED,
        WITHDRAWN,
        EXPIRED,
    )


class DocumentType:
    """Allowed application document types."""

    TAILORED_RESUME = "tailored_resume"
    COVER_LETTER = "cover_letter"

    ALL = (TAILORED_RESUME, COVER_LETTER)


@dataclass
class Application(TimestampedEntity):
    """An application for a job.

    ``job_id`` is a logical reference to the Jobs context — no FK (rule 15).
    """

    id: str = field(default_factory=lambda: str(uuid.uuid7()))
    job_id: str = ""
    status: str = ApplicationStatus.SEEN
    applied_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "status": self.status,
            "applied_at": self.applied_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ApplicationStatusEvent(TimestampedEntity):
    """A single point on the application status timeline.

    Records that the application entered ``status`` at ``changed_at``. The full
    ordered list of events traces the application's lifecycle over time.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid7()))
    application_id: str = ""
    status: str = ApplicationStatus.SEEN
    changed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "status": self.status,
            "changed_at": self.changed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ApplicationFollowUp(TimestampedEntity):
    """A single follow-up on an application (date, note, completion)."""

    id: str = field(default_factory=lambda: str(uuid.uuid7()))
    application_id: str = ""
    scheduled_at: str | None = None
    note: str = ""
    completed_at: str | None = None

    @property
    def completed(self) -> bool:
        return self.completed_at is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "scheduled_at": self.scheduled_at,
            "note": self.note,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ApplicationDocument(TimestampedEntity):
    """A versioned application document (tailored resume / cover letter)."""

    id: str = field(default_factory=lambda: str(uuid.uuid7()))
    application_id: str = ""
    document_type: str = DocumentType.TAILORED_RESUME
    version: int = 1
    content: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "application_id": self.application_id,
            "document_type": self.document_type,
            "version": self.version,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


__all__ = [
    "Application",
    "ApplicationStatusEvent",
    "ApplicationFollowUp",
    "ApplicationDocument",
    "ApplicationStatus",
    "DocumentType",
]
