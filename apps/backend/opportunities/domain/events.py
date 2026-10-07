"""Domain events for the Opportunities bounded context.

Emitted as an opportunity evolves: created, extracted, linked, evaluated, and
status-changed. All events are immutable facts (AGENTS.md rule 16); the default
transport is the in-memory collector.
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


__all__ = [
    "OpportunityCreated",
    "OpportunityExtracted",
    "OpportunityLinked",
    "OpportunityEvaluated",
    "OpportunityStatusChanged",
]
