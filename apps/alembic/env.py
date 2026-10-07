"""Alembic environment configuration for multi-schema, multi-context migrations.

Each bounded context owns its own PostgreSQL schema and migration history.
Migration scripts are organized in separate directories per context:
  - apps/alembic/job/versions/     (job schema)
  - apps/alembic/company/versions/ (company schema)
  - apps/alembic/skill/versions/   (skill schema)
  - apps/alembic/candidate/versions/ (candidate schema)
  - apps/alembic/application/versions/ (application schema)
  - apps/alembic/shared/versions/  (shared schema)

New context branches are created with autogenerate (never by hand) so the
revision-graph references (revision/down_revision/branch_labels) are computed
by Alembic; see docs/database/alembic-guide.md.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

_server_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, os.path.abspath(_server_dir))

from shared.infrastructure.config.app_config import DATABASE_URL
from shared.infrastructure.database.sqlalchemy_config import Base

# Import every context's model package so all tables register with Base.metadata
# (Alembic autogenerate discovers models via Base.metadata).
import jobs.infrastructure.models.job_model  # noqa: F401
import jobs.infrastructure.models.job_analysis_model  # noqa: F401
import jobs.infrastructure.models.job_company_model  # noqa: F401
import jobs.infrastructure.models.misc_models  # noqa: F401
import skills.infrastructure.models.skill_model  # noqa: F401
import companies.infrastructure.models.company_model  # noqa: F401
import rules.infrastructure.models.rule_model  # noqa: F401
import ai.infrastructure.models.llm_configuration_model  # noqa: F401
import processing.infrastructure.models.processing_execution_model  # noqa: F401
import candidates.infrastructure.models.candidate_model  # noqa: F401
import applications.infrastructure.models.application_model  # noqa: F401
import opportunities.infrastructure.models.opportunity_model  # noqa: F401
import roadmaps.infrastructure.models.roadmap_model  # noqa: F401
import placeholders.infrastructure.models.placeholder_model  # noqa: F401
import cities.infrastructure.models.city_model  # noqa: F401
import auth.infrastructure.user_model  # noqa: F401

config = context.config
config.set_main_option('sqlalchemy.url', DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        schema = getattr(obj, "schema", None)
        target = os.environ.get("ALEMBIC_TARGET_SCHEMA")
        if target:
            # Never drop reflected tables that aren't modeled when scoping a
            # context migration (avoids destructive autogenerate).
            if reflected and compare_to is None:
                return False
            if schema != target:
                return False
            return True
        configured_schema = context.get_context().opts.get("schema")
        if schema and configured_schema and schema != configured_schema:
            return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def ensure_widened_version_table(connection) -> None:
    """Widen alembic_version.version_num beyond the default VARCHAR(32).

    Several migration revision IDs (e.g. company_003_add_companies_raw_content)
    are longer than 32 characters, so the table must be created with (or
    altered to) a wider column before alembic stamps those revisions. Alembic
    creates the table lazily with checkfirst=True, so a pre-created table is
    reused as-is. Idempotent: existing databases keep their current column.
    """
    table = "alembic_version"
    if connection.dialect.has_table(connection, table):
        connection.execute(
            text(f"ALTER TABLE {table} ALTER COLUMN version_num TYPE VARCHAR(255)")
        )
    else:
        connection.execute(
            text(f"CREATE TABLE {table} (version_num VARCHAR(255) NOT NULL)")
        )


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            version_table="alembic_version",
        )
        ensure_widened_version_table(connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()