"""SQLAlchemy ORM models for the opportunity schema.

The Opportunities context owns its own PostgreSQL schema. Cross-context
references (``company_id``, ``job_id``) are logical only (AGENTS.md rule 15):
plain columns with NO ForeignKey into other schemas. The FK between
``opportunity_evaluations`` and ``opportunities`` is within the schema
(aggregate + children) and is allowed.
"""

from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.database.sqlalchemy_config import Base


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return str(uuid.uuid7())


class OpportunityModel(Base):
    __tablename__ = "opportunities"
    __table_args__ = {"schema": "opportunity"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="")
    source: Mapped[str] = mapped_column(String, default="manual")
    source_message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    sender: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sender_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    received_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_content: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="")
    extracted_urls: Mapped[str] = mapped_column(Text, default="[]")
    extracted: Mapped[str] = mapped_column(Text, default="{}")
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    job_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="new", index=True)
    evaluation_status: Mapped[str] = mapped_column(String, default="pending")
    fit_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    evaluation: Mapped[str] = mapped_column(Text, default="{}")
    missing_information: Mapped[str] = mapped_column(Text, default="[]")
    application_path: Mapped[str] = mapped_column(Text, default="{}")
    next_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, default=_now_iso)
    updated_at: Mapped[str] = mapped_column(Text, default=_now_iso)


class OpportunityEvaluationModel(Base):
    __tablename__ = "opportunity_evaluations"
    __table_args__ = {"schema": "opportunity"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_id)
    opportunity_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("opportunity.opportunities.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    evaluation_status: Mapped[str] = mapped_column(String, default="complete")
    fit_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    snapshot: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[str] = mapped_column(Text, default=_now_iso)
