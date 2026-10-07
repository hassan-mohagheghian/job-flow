"""Shared test fixtures and configuration.

Uses PostgreSQL exclusively. Tests connect to a test-specific database
derived from DATABASE_URL by appending '_test' to the database name.
The test database is created automatically if it does not exist.
"""

import sys
import os
import re
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv()

# Tests never touch the real TaskIQ broker — use the in-memory broker.
os.environ["TASKIQ_BROKER"] = "memory"

from shared.infrastructure.database.sqlalchemy_config import Base, ensure_schemas
import jobs.infrastructure.models.job_model
import jobs.infrastructure.models.misc_models
import jobs.infrastructure.models.job_company_model
import skills.infrastructure.models.skill_model
import companies.infrastructure.models.company_model
import rules.infrastructure.models.rule_model
import processing.infrastructure.models.processing_execution_model
import candidates.infrastructure.models.candidate_model  # noqa: F401
import applications.infrastructure.models.application_model  # noqa: F401
import opportunities.infrastructure.models.opportunity_model  # noqa: F401
import roadmaps.infrastructure.models.roadmap_model  # noqa: F401
import placeholders.infrastructure.models.placeholder_model  # noqa: F401
import cities.infrastructure.models.city_model  # noqa: F401


def _get_test_db_url() -> str:
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError("DATABASE_URL is required. Set it to a PostgreSQL connection string.")
    m = re.match(r'^(postgresql(?:\+psycopg)?://[^/]+)/(.+)$', url)
    if not m:
        raise RuntimeError(f"Could not parse DATABASE_URL: {url}")
    return f"{m.group(1)}/{m.group(2)}_test"


TEST_DB_URL = os.environ.get('TEST_DATABASE_URL') or _get_test_db_url()


def _ensure_test_database():
    """Create the test database if it does not exist."""
    url = os.environ.get('DATABASE_URL')
    m = re.match(r'^(postgresql(?:\+psycopg)?://[^/]+)/.+$', url)
    admin_url = m.group(1) + '/postgres'
    db_name = TEST_DB_URL.split('/')[-1]
    try:
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE {db_name}"))
        admin_engine.dispose()
    except Exception:
        pass


_ensure_test_database()


@pytest.fixture(scope="session")
def _engine():
    from sqlalchemy import create_engine, text
    from shared.infrastructure.database.sqlalchemy_config import SCHEMAS
    engine = create_engine(TEST_DB_URL)
    with engine.connect() as conn:
        for schema in SCHEMAS:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sa_session(_engine):
    connection = _engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def mock_get_session(sa_session):
    with patch('dependencies.get_session_sync', return_value=sa_session):
        yield sa_session


@pytest.fixture
def mock_get_session_worker(sa_session):
    with patch('jobs.infrastructure.workers.worker.get_session_sync', return_value=sa_session):
        yield sa_session


@pytest.fixture
def client(sa_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from fastapi.responses import JSONResponse
    from dependencies import (
        get_session, get_session_sync, get_job_repo, get_skill_repo,
        get_company_repo, get_pending_repo, get_rule_repo,
        get_summary_repo, get_company_link_repo, get_company_intelligence_repo,
        get_processing_execution_repo,
        get_candidate_repo, get_candidate_profile_repo, get_candidate_source_repo,
        get_application_repo, get_follow_up_repo, get_document_repo,
        get_opportunity_repo, get_opportunity_evaluation_repo, get_opportunity_service,
        get_roadmap_repo, get_roadmap_service, get_city_repo,
    )
    from exceptions import AppError
    from jobs.infrastructure.repositories.sa_job_repository import SQLAlchemyJobRepository
    from skills.infrastructure.repositories.sa_skill_repository import SQLAlchemySkillRepository
    from companies.infrastructure.repositories.sa_company_repository import SQLAlchemyCompanyRepository
    from rules.infrastructure.repositories.sa_rule_repository import SQLAlchemyRuleRepository
    from jobs.infrastructure.repositories.sa_summary_repository import SQLAlchemySummaryRepository
    from companies.infrastructure.repositories.sa_company_link_repository import SQLAlchemyCompanyLinkRepository
    from companies.infrastructure.repositories.sa_company_intelligence_repository import SQLAlchemyCompanyIntelligenceRepository
    from processing.infrastructure.repositories.sa_processing_execution_repository import SQLAlchemyProcessingExecutionRepository
    from candidates.infrastructure.repositories.sa_candidate_repository import SQLAlchemyCandidateRepository
    from candidates.infrastructure.repositories.sa_candidate_profile_repository import SQLAlchemyCandidateProfileRepository
    from candidates.infrastructure.repositories.sa_candidate_source_repository import SQLAlchemyCandidateSourceRepository
    from applications.infrastructure.repositories.sa_application_repository import SQLAlchemyApplicationRepository
    from applications.infrastructure.repositories.sa_follow_up_repository import SQLAlchemyFollowUpRepository
    from applications.infrastructure.repositories.sa_document_repository import SQLAlchemyDocumentRepository
    from opportunities.infrastructure.repositories.sa_opportunity_repository import (
        SQLAlchemyOpportunityEvaluationRepository,
        SQLAlchemyOpportunityRepository,
    )
    from roadmaps.infrastructure.repositories.sa_roadmap_repository import SQLAlchemyRoadmapRepository
    from roadmaps.application.services.roadmap_service import RoadmapService
    from roadmaps.domain.event_publisher import InMemoryEventCollector as RoadmapInMemoryEventCollector
    from cities.infrastructure.repositories.sa_city_repository import SQLAlchemyCityRepository
    from shared.presentation.api.root_router import api_router

    app = FastAPI(title="Test API")

    @app.exception_handler(AppError)
    async def app_error_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.detail, "details": getattr(exc, "details", None)}},
        )

    def override_get_session():
        yield sa_session

    def override_get_session_sync():
        return sa_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_session_sync] = override_get_session_sync

    # Override auth — all tests run as "test-user"
    from auth.presentation.api.auth_router import get_current_user as _get_current_user
    from auth.domain.user import User as _User
    _test_user = _User(id="test-user", username="test", display_name="Test User", password_hash="")
    app.dependency_overrides[_get_current_user] = lambda: _test_user

    app.dependency_overrides[get_job_repo] = lambda: SQLAlchemyJobRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_skill_repo] = lambda: SQLAlchemySkillRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_company_repo] = lambda: SQLAlchemyCompanyRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_pending_repo] = lambda: SQLAlchemyJobRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_rule_repo] = lambda: SQLAlchemyRuleRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_summary_repo] = lambda: SQLAlchemySummaryRepository(sa_session)
    app.dependency_overrides[get_company_link_repo] = lambda: SQLAlchemyCompanyLinkRepository(sa_session)
    app.dependency_overrides[get_company_intelligence_repo] = lambda: SQLAlchemyCompanyIntelligenceRepository(sa_session)
    app.dependency_overrides[get_processing_execution_repo] = lambda: SQLAlchemyProcessingExecutionRepository(sa_session)
    app.dependency_overrides[get_candidate_repo] = lambda: SQLAlchemyCandidateRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_candidate_profile_repo] = lambda: SQLAlchemyCandidateProfileRepository(sa_session)
    app.dependency_overrides[get_candidate_source_repo] = lambda: SQLAlchemyCandidateSourceRepository(sa_session)
    app.dependency_overrides[get_application_repo] = lambda: SQLAlchemyApplicationRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_opportunity_repo] = lambda: SQLAlchemyOpportunityRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_opportunity_evaluation_repo] = lambda: SQLAlchemyOpportunityEvaluationRepository(sa_session)
    app.dependency_overrides[get_opportunity_service] = lambda: get_opportunity_service(
        opportunity_repo=SQLAlchemyOpportunityRepository(sa_session, user_id="test-user"),
        evaluation_repo=SQLAlchemyOpportunityEvaluationRepository(sa_session),
        job_repo=SQLAlchemyJobRepository(sa_session, user_id="test-user"),
        company_repo=SQLAlchemyCompanyRepository(sa_session, user_id="test-user"),
        skill_repo=SQLAlchemySkillRepository(sa_session, user_id="test-user"),
        profile_repo=SQLAlchemyCandidateProfileRepository(sa_session),
        rule_repo=SQLAlchemyRuleRepository(sa_session, user_id="test-user"),
    )
    app.dependency_overrides[get_follow_up_repo] = lambda: SQLAlchemyFollowUpRepository(sa_session)
    app.dependency_overrides[get_document_repo] = lambda: SQLAlchemyDocumentRepository(sa_session)
    app.dependency_overrides[get_roadmap_repo] = lambda: SQLAlchemyRoadmapRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_city_repo] = lambda: SQLAlchemyCityRepository(sa_session, user_id="test-user")
    app.dependency_overrides[get_roadmap_service] = lambda: RoadmapService(
        SQLAlchemyRoadmapRepository(sa_session, user_id="test-user"),
        SQLAlchemySkillRepository(sa_session, user_id="test-user"),
        RoadmapInMemoryEventCollector(),
    )
    app.include_router(api_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
