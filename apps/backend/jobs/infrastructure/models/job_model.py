"""SQLAlchemy ORM models for the jobs table."""

from datetime import datetime
from typing import Optional
import uuid

import sqlalchemy as sa
from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.database.sqlalchemy_config import Base

def _now_iso() -> str:
    return datetime.utcnow().isoformat()


class JobModel(Base):
    """SQLAlchemy model for the jobs table."""

    __tablename__ = "jobs"
    __table_args__ = (
        sa.Index("ix_job_jobs_user_deleted_created", "user_id", "deleted", "created_at"),
        sa.Index("ix_job_jobs_work_types_gin", "work_types", postgresql_using="gin"),
        sa.Index("ix_job_jobs_employment_types_gin", "employment_types", postgresql_using="gin"),
        sa.Index("ix_job_jobs_tags_gin", "tags", postgresql_using="gin"),
        {"schema": "job"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid7()))
    company: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    salary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stack: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    visa: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    applicants: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    posted: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    action: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    workflow_log: Mapped[str] = mapped_column(Text, default="[]")
    deleted: Mapped[int] = mapped_column(Integer, default=0)
    work_types: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=sa.text("'[]'::jsonb"), nullable=False
    )
    employment_types: Mapped[list[str]] = mapped_column(
        JSONB,
        default=lambda: ["Full-time"],
        server_default=sa.text("""'["Full-time"]'::jsonb"""),
        nullable=False,
    )
    raw_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    adv_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    see_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    apply_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fit_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    company_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    city_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(Text, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(Text, default=datetime.utcnow, onupdate=datetime.utcnow)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    apply_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    response_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    response_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rescoring: Mapped[int] = mapped_column(Integer, default=0)
    pinned: Mapped[int] = mapped_column("favorite", Integer, default=0)
    dismissed: Mapped[int] = mapped_column("dismissed", Integer, default=0)
    tags: Mapped[list[str]] = mapped_column(
        "tags", JSONB, default=list, server_default=sa.text("'[]'::jsonb"), nullable=False
    )
    links: Mapped[str] = mapped_column(Text, default="[]")
    source: Mapped[Optional[str]] = mapped_column(String, default="web")
    status: Mapped[str] = mapped_column(String, default="imported")
    queue_order: Mapped[int] = mapped_column(Integer, default=0)
    current_node: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    progress_pct: Mapped[float] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_step: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    failure_timestamp: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    easy_apply: Mapped[Optional[bool]] = mapped_column(Integer, nullable=True, default=None)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="")
    source_site_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)


class JobSourceModel(Base):
    """SQLAlchemy model for job_sources — canonical job boards the listings
    were posted on (derived from the job URL hostname at ingestion)."""

    __tablename__ = "job_sources"
    __table_args__ = (
        sa.Index("uq_job_sources_user_domain", "user_id", "normalized_domain", unique=True),
        {"schema": "job"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid7()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="")
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    normalized_domain: Mapped[Optional[str]] = mapped_column(String, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[Optional[str]] = mapped_column(Text, default=_now_iso)
    updated_at: Mapped[Optional[str]] = mapped_column(Text, default=_now_iso, onupdate=_now_iso)
