"""Domain events for the Opportunities bounded context.

Emitted as an opportunity evolves: created, extracted, linked, evaluated,
status-changed, moved-to-job. All events are immutable facts (AGENTS.md rule
16); the default transport is the in-memory collector.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class OpportunityCreated(DomainEvent):
    """A new inbound opportunity was stored."""

    opportunity_id: str = ""
    source: str = ""
    event_type: str = "opportunity.created"


@dataclass(frozen=True)
class OpportunityExtracted(DomainEvent):
    """The message was extracted into partial structured fields."""

    opportunity_id: str = ""
    has_role: bool = False
    has_company: bool = False
    url_count: int = 0
    event_type: str = "opportunity.extracted"


@dataclass(frozen=True)
class OpportunityLinked(DomainEvent):
    """The opportunity was linked to existing job/company rows."""

    opportunity_id: str = ""
    job_id: str | None = None
    company_id: str | None = None
    event_type: str = "opportunity.linked"


@dataclass(frozen=True)
class OpportunityEvaluated(DomainEvent):
    """An evaluation snapshot was appended (scored or pending)."""

    opportunity_id: str = ""
    status: str = ""
    overall_score: int | None = None
    recommendation: str | None = None
    event_type: str = "opportunity.evaluated"


@dataclass(frozen=True)
class OpportunityStatusChanged(DomainEvent):
    """The opportunity moved along the funnel."""

    opportunity_id: str = ""
    status: str = ""
    event_type: str = "opportunity.status.changed"


@dataclass(frozen=True)
class OpportunityNoteAdded(DomainEvent):
    """A follow-up note was added to an opportunity."""

    opportunity_id: str = ""
    note_id: str = ""
    event_type: str = "opportunity.note.added"


@dataclass(frozen=True)
class OpportunityNoteDeleted(DomainEvent):
    """A follow-up note was removed."""

    opportunity_id: str = ""
    note_id: str = ""
    event_type: str = "opportunity.note.deleted"


@dataclass(frozen=True)
class OpportunityLinkAdded(DomainEvent):
    """A user link (titled URL) was added to an opportunity."""

    opportunity_id: str = ""
    link_id: str = ""
    event_type: str = "opportunity.link.added"


@dataclass(frozen=True)
class OpportunityLinkDeleted(DomainEvent):
    """A user link was removed."""

    opportunity_id: str = ""
    link_id: str = ""
    event_type: str = "opportunity.link.deleted"


@dataclass(frozen=True)
class OpportunityMovedToJob(DomainEvent):
    """An evaluated opportunity was linked to (or created as) a job row."""

    opportunity_id: str = ""
    job_id: str | None = None
    job_title: str | None = None
    overall_score: int | None = None
    recommendation: str | None = None
    created_job: bool = False
    event_type: str = "opportunity.moved_to_job"


__all__ = [
    "OpportunityCreated",
    "OpportunityExtracted",
    "OpportunityLinked",
    "OpportunityEvaluated",
    "OpportunityStatusChanged",
    "OpportunityNoteAdded",
    "OpportunityNoteDeleted",
    "OpportunityLinkAdded",
    "OpportunityLinkDeleted",
    "OpportunityMovedToJob",
]
