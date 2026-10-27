"""phase 0 job storage cleanup: JSONB arrays, cascade FKs, dead columns

Changes (all in the ``job`` schema, no cross-context FKs):

* ``jobs.work_types`` / ``jobs.employment_types`` / ``jobs.tags`` become
  ``jsonb`` arrays (GIN indexed) and non-null.
* ``jobs.match`` / ``jobs.score`` / ``jobs.success`` / ``jobs.locations`` are
  dropped — they were never populated by the Job Analysis workflow.
* ``job_analysis.job_id`` and ``summaries.job_id`` get cascade FKs to
  ``job.jobs.id`` (orphan rows are removed first).
* A composite ``(user_id, deleted, created_at)`` index backs the list query.

Downgrade restores the previous column types/columns (dropped column data is
not recoverable; they were empty in practice) and removes the new indexes and
FKs. Orphan analysis/summary rows removed on upgrade are intentionally not
restored.

Revision ID: job_010
Revises: 807af848eab4
Create Date: 2026-10-26 19:59:34.284379
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "job_010"
down_revision: Union[str, None] = "807af848eab4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "job"

JSONB_COLUMNS = {
    # column: default fragment used when the legacy value is NULL/empty
    "work_types": "'[]'::jsonb",
    "employment_types": """'["Full-time"]'::jsonb""",
    "tags": "'[]'::jsonb",
}

DROPPED_COLUMNS = ("match", "score", "success", "locations")

INDEXES = (
    ("ix_job_jobs_user_deleted_created", ["user_id", "deleted", "created_at"], False),
    ("ix_job_jobs_work_types_gin", ["work_types"], True),
    ("ix_job_jobs_employment_types_gin", ["employment_types"], True),
    ("ix_job_jobs_tags_gin", ["tags"], True),
)

FK_JOB_ANALYSIS = "fk_job_analysis_job_id_jobs"
FK_SUMMARIES = "fk_summaries_job_id_jobs"


def _inspector():
    return sa.inspect(op.get_bind())


def _column_names(table: str) -> set[str]:
    return {c["name"] for c in _inspector().get_columns(table, schema=SCHEMA)}


def _index_names(table: str) -> set[str]:
    return {i["name"] for i in _inspector().get_indexes(table, schema=SCHEMA)}


def _fk_names(table: str) -> set[str]:
    return {fk["name"] for fk in _inspector().get_foreign_keys(table, schema=SCHEMA)}


def _upgrade_column_to_jsonb(column: str, default_sql: str) -> None:
    """Convert a legacy Text JSON column to JSONB, normalizing bad values."""
    cols = {c["name"]: c for c in _inspector().get_columns("jobs", schema=SCHEMA)}
    col = cols.get(column)
    if col is None:
        return

    if not isinstance(col["type"], postgresql.JSONB):
        # The legacy Text default cannot be cast implicitly, so drop it before
        # the type change and install the JSONB default afterwards.
        op.alter_column(
            "jobs",
            column,
            server_default=None,
            existing_type=col["type"],
            existing_nullable=col["nullable"],
            schema=SCHEMA,
        )
        # ``USING`` handles legacy plain-text values by wrapping them in an
        # array; empty/NULL values fall back to the column default.
        op.alter_column(
            "jobs",
            column,
            existing_type=col["type"],
            type_=postgresql.JSONB(astext_type=sa.Text()),
            existing_nullable=col["nullable"],
            postgresql_using=(
                "CASE "
                f"WHEN {column} IS NULL OR btrim({column}) = '' THEN {default_sql} "
                f"WHEN left(btrim({column}), 1) IN ('[', '{{') THEN btrim({column})::jsonb "
                f"ELSE jsonb_build_array(btrim({column})) "
                "END"
            ),
            schema=SCHEMA,
        )

    op.alter_column(
        "jobs",
        column,
        server_default=sa.text(default_sql),
        nullable=False,
        schema=SCHEMA,
    )


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # ── JSONB arrays ────────────────────────────────────────────────
    for column, default_sql in JSONB_COLUMNS.items():
        _upgrade_column_to_jsonb(column, default_sql)

    # ── Drop never-populated columns ────────────────────────────────
    existing_columns = _column_names("jobs")
    for column in DROPPED_COLUMNS:
        if column in existing_columns:
            op.drop_column("jobs", column, schema=SCHEMA)

    # ── Same-schema cascade FKs ─────────────────────────────────────
    # Orphan child rows would make FK creation fail; they are unreachable
    # from any job and cannot be recovered, so remove them first.
    op.execute(
        "DELETE FROM job.job_analysis a "
        "WHERE NOT EXISTS (SELECT 1 FROM job.jobs j WHERE j.id = a.job_id)"
    )
    op.execute(
        "DELETE FROM job.summaries s "
        "WHERE s.job_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM job.jobs j WHERE j.id = s.job_id)"
    )

    if FK_JOB_ANALYSIS not in _fk_names("job_analysis"):
        op.create_foreign_key(
            FK_JOB_ANALYSIS,
            "job_analysis",
            "jobs",
            ["job_id"],
            ["id"],
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
            ondelete="CASCADE",
        )

    if FK_SUMMARIES not in _fk_names("summaries"):
        op.create_foreign_key(
            FK_SUMMARIES,
            "summaries",
            "jobs",
            ["job_id"],
            ["id"],
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
            ondelete="CASCADE",
        )

    # ── List-query indexes ──────────────────────────────────────────
    existing_indexes = _index_names("jobs")
    for name, columns, is_gin in INDEXES:
        if name not in existing_indexes:
            op.create_index(
                name,
                "jobs",
                columns,
                unique=False,
                schema=SCHEMA,
                postgresql_using="gin" if is_gin else None,
            )


def downgrade() -> None:
    existing_indexes = _index_names("jobs")
    for name, _columns, _is_gin in INDEXES:
        if name in existing_indexes:
            op.drop_index(name, table_name="jobs", schema=SCHEMA)

    if FK_SUMMARIES in _fk_names("summaries"):
        op.drop_constraint(FK_SUMMARIES, "summaries", schema=SCHEMA, type_="foreignkey")

    if FK_JOB_ANALYSIS in _fk_names("job_analysis"):
        op.drop_constraint(FK_JOB_ANALYSIS, "job_analysis", schema=SCHEMA, type_="foreignkey")

    # JSONB -> Text (arrays serialize back to their JSON text form).
    columns = {c["name"]: c for c in _inspector().get_columns("jobs", schema=SCHEMA)}
    for column in JSONB_COLUMNS:
        col = columns.get(column)
        if col is None or not isinstance(col["type"], postgresql.JSONB):
            continue
        op.alter_column(
            "jobs",
            column,
            server_default=None,
            existing_type=col["type"],
            existing_nullable=col["nullable"],
            schema=SCHEMA,
        )
        op.alter_column(
            "jobs",
            column,
            existing_type=col["type"],
            type_=sa.Text(),
            existing_nullable=col["nullable"],
            postgresql_using=f"{column}::text",
            schema=SCHEMA,
        )

    op.alter_column(
        "jobs",
        "work_types",
        server_default=sa.text("'[]'::text"),
        nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "jobs",
        "employment_types",
        server_default=sa.text("""'["Full-time"]'::text"""),
        nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "jobs",
        "tags",
        server_default=sa.text("'[]'::text"),
        nullable=False,
        schema=SCHEMA,
    )

    # Restore the removed columns (empty by construction; data not recoverable).
    existing_columns = _column_names("jobs")
    if "match" not in existing_columns:
        op.add_column("jobs", sa.Column("match", sa.String(), nullable=True), schema=SCHEMA)
    if "score" not in existing_columns:
        op.add_column("jobs", sa.Column("score", sa.String(), nullable=True), schema=SCHEMA)
    if "success" not in existing_columns:
        op.add_column("jobs", sa.Column("success", sa.String(), nullable=True), schema=SCHEMA)
    if "locations" not in existing_columns:
        op.add_column(
            "jobs",
            sa.Column("locations", sa.Text(), server_default=sa.text("'[]'::text"), nullable=True),
            schema=SCHEMA,
        )
