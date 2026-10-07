"""Opportunity aggregate entities.

The Opportunity is the aggregate root of the Opportunities bounded context. It
represents a single inbound recruiting message and its progressive enrichment:
extract fields → resolve against existing jobs/companies → evaluate against
the candidate profile and rules → track a funnel status and next action.

Cross-context references (``company_id``, ``job_id``) are logical references
only — there are no FKs into other schemas (AGENTS.md rule 15). The context
never creates jobs, companies, or skills.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any
import uuid


class OpportunitySource:
    """Where the inbound message came from.

    Only manual paste ingestion exists in phase one; ``gmail`` / ``linkedin``
    are reserved vocabulary so future integrations feed the same pipeline.
    """

    MANUAL = "manual"
    GMAIL = "gmail"
    LINKEDIN = "linkedin"

    ALL = (MANUAL, GMAIL, LINKEDIN)


class OpportunityStatus:
    """Lifecycle of an opportunity.

    ``needs_info`` is an explicit state: extraction/resolution ran but there is
    not enough information to score. Terminal states are ``rejected`` /
    ``closed``.
    """

    NEW = "new"
    EXTRACTED = "extracted"
    ENRICHING = "enriching"
    NEEDS_INFO = "needs_info"
    EVALUATED = "evaluated"
    READY_TO_APPLY = "ready_to_apply"
    APPLIED = "applied"
    REPLIED = "replied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    CLOSED = "closed"

    ALL = (
        NEW,
        EXTRACTED,
        ENRICHING,
        NEEDS_INFO,
        EVALUATED,
        READY_TO_APPLY,
        APPLIED,
        REPLIED,
        INTERVIEW,
        REJECTED,
        CLOSED,
    )

    TERMINAL = (REJECTED, CLOSED)

    TRANSITIONS: dict[str, tuple[str, ...]] = {
        NEW: (EXTRACTED, ENRICHING, EVALUATED, NEEDS_INFO, READY_TO_APPLY),
        EXTRACTED: (ENRICHING, EVALUATED, NEEDS_INFO, READY_TO_APPLY),
        ENRICHING: (EVALUATED, NEEDS_INFO, READY_TO_APPLY),
        NEEDS_INFO: (ENRICHING, EVALUATED, READY_TO_APPLY, REJECTED, CLOSED),
        EVALUATED: (READY_TO_APPLY, APPLIED, REJECTED, CLOSED),
        READY_TO_APPLY: (APPLIED, REJECTED, CLOSED),
        APPLIED: (REPLIED, INTERVIEW, REJECTED, CLOSED),
        REPLIED: (INTERVIEW, REJECTED, CLOSED),
        INTERVIEW: (REJECTED, CLOSED),
        REJECTED: (),
        CLOSED: (),
    }


class EvaluationStatus:
    PENDING = "pending"
    COMPLETE = "complete"

    ALL = (PENDING, COMPLETE)


class FieldState:
    """Explicit uncertainty for every extracted field."""

    KNOWN = "known"
    UNKNOWN = "unknown"
    INFERRED = "inferred"
    NEEDS_VERIFICATION = "needs_verification"

    ALL = (KNOWN, UNKNOWN, INFERRED, NEEDS_VERIFICATION)


@dataclass
class Opportunity:
    """An inbound opportunity and its current enrichment state."""

    id: str = field(default_factory=lambda: str(uuid.uuid7()))
    source: str = OpportunitySource.MANUAL
    source_message_id: str | None = None
    sender: str | None = None
    sender_email: str | None = None
    received_at: str | None = None
    subject: str | None = None
    raw_content: str = ""
    content_hash: str = ""
    extracted_urls: list[str] = field(default_factory=list)
    extracted: dict[str, Any] = field(default_factory=dict)
    company_id: str | None = None
    company_name: str | None = None
    job_id: str | None = None
    job_title: str | None = None
    status: str = OpportunityStatus.NEW
    evaluation_status: str = EvaluationStatus.PENDING
    fit_score: int | None = None
    success_score: int | None = None
    overall_score: int | None = None
    recommendation: str | None = None
    evaluation: dict[str, Any] = field(default_factory=dict)
    missing_information: list[str] = field(default_factory=list)
    application_path: dict[str, Any] = field(default_factory=dict)
    next_action: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def title(self) -> str:
        """Display title: extracted role, else subject, else fallback."""
        role = (self.extracted or {}).get("role_title")
        if role:
            return str(role)
        if self.job_title:
            return str(self.job_title)
        if self.subject:
            return str(self.subject)
        return "Unknown role"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "source_message_id": self.source_message_id,
            "sender": self.sender,
            "sender_email": self.sender_email,
            "received_at": self.received_at,
            "subject": self.subject,
            "raw_content": self.raw_content,
            "content_hash": self.content_hash,
            "extracted_urls": list(self.extracted_urls),
            "extracted": dict(self.extracted),
            "company_id": self.company_id,
            "company_name": self.company_name,
            "job_id": self.job_id,
            "job_title": self.job_title,
            "status": self.status,
            "evaluation_status": self.evaluation_status,
            "fit_score": self.fit_score,
            "success_score": self.success_score,
            "overall_score": self.overall_score,
            "recommendation": self.recommendation,
            "evaluation": dict(self.evaluation),
            "missing_information": list(self.missing_information),
            "application_path": dict(self.application_path),
            "next_action": self.next_action,
            "title": self.title(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class OpportunityEvaluation:
    """An immutable evaluation snapshot for an opportunity."""

    id: str = field(default_factory=lambda: str(uuid.uuid7()))
    opportunity_id: str = ""
    status: str = OpportunityStatus.EVALUATED
    evaluation_status: str = EvaluationStatus.COMPLETE
    fit_score: int | None = None
    success_score: int | None = None
    overall_score: int | None = None
    recommendation: str | None = None
    snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "opportunity_id": self.opportunity_id,
            "status": self.status,
            "evaluation_status": self.evaluation_status,
            "fit_score": self.fit_score,
            "success_score": self.success_score,
            "overall_score": self.overall_score,
            "recommendation": self.recommendation,
            "snapshot": dict(self.snapshot),
            "created_at": self.created_at,
        }


__all__ = [
    "Opportunity",
    "OpportunityEvaluation",
    "OpportunitySource",
    "OpportunityStatus",
    "EvaluationStatus",
    "FieldState",
]
