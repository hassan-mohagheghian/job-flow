"""SQLAlchemy ORM models for summaries (job schema)."""

from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.infrastructure.database.sqlalchemy_config import Base


class SummaryModel(Base):
    __tablename__ = "summaries"
    __table_args__ = {"schema": "job"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("job.jobs.id", ondelete="CASCADE"), nullable=True
    )
    company: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    match: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    score: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resumeFit: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True, default="")
