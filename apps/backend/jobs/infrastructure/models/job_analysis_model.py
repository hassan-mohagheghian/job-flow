"""SQLAlchemy ORM model for the job_analysis table.

Stores the canonical full LLM analysis for a job (fields, scores,
recommendation, summary, skills) produced by the Job Analysis workflow.
"""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.database.sqlalchemy_config import Base


class JobAnalysisModel(Base):
    """SQLAlchemy model for the job_analysis table."""

    __tablename__ = "job_analysis"
    __table_args__ = (
        UniqueConstraint("job_id", "user_id", name="uq_job_analysis_job_user"),
        {"schema": "job"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job.jobs.id", ondelete="CASCADE"), nullable=False
    )
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fit_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    apply_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    schema_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    generated_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="")
