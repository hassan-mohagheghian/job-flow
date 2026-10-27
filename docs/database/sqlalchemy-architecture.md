# SQLAlchemy Architecture

## Overview

The persistence layer uses SQLAlchemy 2.x with the declarative base pattern. All database access goes through repository implementations that use SQLAlchemy sessions, hiding the underlying database details from the domain and application layers.

The database uses a **schema-per-bounded-context** architecture, isolating each domain's tables in its own PostgreSQL schema. This enables independent versioning via Alembic and clean separation of concerns. Foreign keys are allowed **within** a bounded context's schema (aggregate + children); **cross-context links are logical references only** — a plain id column with no FK constraint (AGENTS.md rule 15), so schemas stay decoupled for a future microservice split.

## Key Components

### Engine & Session

- **Engine**: `shared/infrastructure/database/sqlalchemy_config.py` — PostgreSQL-only engine created from the `DATABASE_URL` environment variable
  - Uses psycopg as the driver, `NullPool` for connection pooling, and `ensure_schemas()` to create the per-context schemas
- **SessionLocal**: Session factory bound to the engine, creates request-scoped sessions
- **get_session()**: FastAPI dependency that yields a session with auto-commit/rollback

### Database URL Configuration

```python
# shared/infrastructure/config/app_config.py
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required.")
```

- `DATABASE_URL` is **required** — a PostgreSQL connection string
  (`postgresql+psycopg://user:pass@host/dbname`). Plain `postgresql://` URLs
  are normalized to the psycopg v3 dialect automatically.

### Engine Creation

```python
# shared/infrastructure/database/sqlalchemy_config.py
engine = create_engine(DATABASE_URL, echo=False, connect_args={}, poolclass=NullPool)

def ensure_schemas():
    with engine.connect() as conn:
        for schema in SCHEMAS:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()
```

### Declarative Base

```python
# shared/infrastructure/database/sqlalchemy_config.py
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })
```

All ORM models inherit from this base. The naming convention ensures consistent constraint naming across all schemas.

### Schema-Per-Context

| Schema | Context | Tables |
|--------|---------|--------|
| `job` | Job Processing | `jobs`, `job_analysis`, `job_companies`, `job_sources`, `summaries`, `generation_history` |
| `company` | Company Intelligence | `companies`, `company_intelligence`, `company_links` |
| `skill` | Skills Management | `skills`, `skill_aliases`, `skill_relationships` |
| `candidate` | Candidate Profile | `candidates`, `candidate_profiles`, `candidate_sources`, `candidate_skills`, `candidate_experiences`, `candidate_projects`, `candidate_educations`, `candidate_certificates`, `candidate_interests`, `candidate_languages`, `candidate_profile_versions` |
| `shared` | Shared/Cross-Cutting | `rules`, `cities` |

Models declare their schema via `__table_args__`:

```python
class JobModel(Base):
    __tablename__ = "jobs"
    __table_args__ = {"schema": "job"}
```

Foreign keys use fully-qualified table names **only within a single schema**
(same bounded context):

```python
profile_id = Column(UUID, ForeignKey("candidate.candidate_profiles.id"), nullable=False)
```

Cross-context links are **plain columns without** `ForeignKey(...)` — e.g.
`candidate_skills.skill_id` references `skill.skills.id` logically only, with
integrity enforced at the repository layer (AGENTS.md rule 15).

### Jobs storage decisions (phase 0)

`job.jobs` is intentionally a single wide table. It is the read model for the
Jobs list (scores, sort keys, status flags), so splitting it into child tables
would add joins to every page request without improving integrity. The
following choices are deliberate:

| Concern | Storage | Rationale |
|---------|---------|-----------|
| Identity / scalars (`title`, `company`, `location`, `url`, `status`, dates, flags) | Columns | 1:1 with the job; filtered and sorted directly |
| Scores (`fit_score`, `success_score`, `overall_score`) | Columns (denormalized) | The list sorts/filters without joining `job_analysis`; written by one place (`PersistNode`) |
| `work_types`, `employment_types` | `jsonb` arrays + GIN | Small closed vocabularies (1–3 values); containment filters (`@>`) are indexable |
| `tags` | `jsonb` array + GIN | User-managed free-form labels; still no separate tags table in this phase |
| `stack` | `text` | Free-text prose extracted by the analysis; job↔skill links already live in `skill.skill_mentions` (cross-context, logical) |
| `notes`, `links`, `workflow_log` | `text` (JSON) | Not filtered; editors own the shape |
| `raw_description`, `structured_description`, `description` | `text` | Multi-KB payloads, TOASTed; the list query loads only its projection |

Same-context integrity is enforced by FKs: `job_analysis.job_id` and
`summaries.job_id` cascade on job delete, and `job_companies.job_id` already
did. Company, city and skill references stay logical (cross-context).


### ORM Models

Located in context-specific model files:

| File | Schema | Tables |
|------|--------|--------|
| `jobs/infrastructure/models/job_model.py` | `job` | `jobs` |
| `skills/infrastructure/models/skill_model.py` | `skill` | `skills`, `skill_aliases`, `skill_relationships` |
| `companies/infrastructure/models/company_model.py` | `company` | `companies`, `company_intelligence`, `company_links` |
| `candidates/infrastructure/models/candidate_model.py` | `candidate` | `candidates`, `candidate_profiles`, `candidate_sources`, `candidate_skills`, `candidate_experiences`, `candidate_projects`, `candidate_educations`, `candidate_certificates`, `candidate_interests`, `candidate_languages`, `candidate_profile_versions` |
| `shared/infrastructure/database/models/misc_models.py` | `job`, `shared` | `summaries`, `resumes`, `rules`, `cities` |

All models are imported into `apps/alembic/env.py` (and `db.py::init_db`) so
Alembic can autogenerate migrations for every schema.

### Domain-to-Database Mapping

Located in `infrastructure/database/mappers.py`:

- `*_model_to_dict()` — converts ORM model to domain dictionary
- `dict_to_*_model()` — converts domain dictionary to ORM model

Mapping happens in the infrastructure layer, keeping the domain layer clean.

### Repository Pattern

- **Domain interfaces**: `domain/repositories/` (ABCs)
- **SQLAlchemy implementations**: `infrastructure/database/sa_*_repository.py`

Repositories accept a `Session` in their constructor and use it for all database operations.

## Session Lifecycle

```
Request arrives
  → get_session() yields a new Session
    → Route handler uses repository (which uses the session)
      → Session commits on success, rolls back on error
        → Session closes in finally block
```

## Testing

Tests use PostgreSQL exclusively. The test database is derived from
`DATABASE_URL` by appending a `_test` suffix to the database name and is
created automatically if it does not exist (`apps/backend/tests/conftest.py`):

```python
@pytest.fixture(scope="session")
def _engine():
    engine = create_engine(TEST_DB_URL)
    with engine.connect() as conn:
        for schema in SCHEMAS:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
```

CI runs the test suite against a PostgreSQL service container (see
`.github/workflows/ci.yml`).