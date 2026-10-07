"""SQLAlchemy engine, session, and Base configuration.

This module provides:
- SQLAlchemy 2.x declarative Base with schema-aware naming convention
- Engine creation for PostgreSQL
- Session factory for request-scoped sessions
- Schema initialization for PostgreSQL (per bounded context)
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from shared.infrastructure.config.app_config import DATABASE_URL

_naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_naming_convention)


SCHEMAS = {
    "auth": ["users"],
    "job": ["jobs", "summaries"],
    "company": ["companies", "company_intelligence", "company_links"],
    "skill": ["skills", "skill_aliases", "skill_relationships"],
    "ai": ["llm_configurations"],
    "processing": ["processing_executions"],
    "candidate": [
        "candidates",
        "candidate_profiles",
        "candidate_sources",
        "candidate_skills",
        "candidate_experiences",
        "candidate_projects",
        "candidate_educations",
        "candidate_certificates",
        "candidate_interests",
        "candidate_languages",
        "candidate_profile_versions",
    ],
    "application": [
        "applications",
        "application_follow_ups",
        "application_documents",
        "application_status_timeline",
    ],
    "opportunity": [
        "opportunities",
        "opportunity_evaluations",
    ],
    "roadmap": [
        "roadmaps",
        "roadmap_goals",
        "roadmap_milestones",
        "roadmap_tasks",
        "roadmap_skill_links",
        "roadmap_notes",
        "roadmap_resources",
    ],
    "placeholders": ["placeholders"],
    "city": ["cities"],
    "shared": ["rules", "metadata", "generation_history", "alembic_version"],
}


engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={},
    poolclass=NullPool,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    expire_on_commit=False,
)


def ensure_schemas():
    from sqlalchemy import text
    with engine.connect() as conn:
        for schema in SCHEMAS:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()