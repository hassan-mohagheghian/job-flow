"""add job sources

Dashboard feature: canonical job-source entities for the jobs the user
imports, derived from each job URL hostname at ingestion
(see docs/api/jobs/job-sources-dashboard.md).

- Creates ``job.job_sources`` (unique per user + normalized_domain).
- Adds ``job.jobs.source_site_id`` (logical reference, indexed).
- Backfills historical jobs in resumable batches; rows whose URL cannot be
  canonicalized stay NULL (dashboard "Unknown").

Revision ID: job_009
Revises: opportunity_003
Create Date: 2026-10-17 16:27:44.420156
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

from jobs.domain.services.job_source_rules import display_name_for_domain, resolve_source
from shared.infrastructure.process.logging_config import get_logger

# revision identifiers, used by Alembic.
revision: str = "job_009"
down_revision: Union[str, None] = "opportunity_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

log = get_logger("alembic.job_009")

_BATCH_SIZE = 500


def _backfill_source_sites(bind) -> None:
    """Batched, resumable backfill of jobs.source_site_id from job URLs.

    One source row per user + normalized domain (reused on conflict, so
    re-runs are idempotent and duplicates collapse onto the first row).
    """
    inserted: dict[tuple[str, str], str] = {}

    while True:
        rows = bind.execute(
            text(
                'SELECT id, url, user_id, created_at FROM job.jobs '
                "WHERE deleted = 0 AND source_site_id IS NULL "
                'AND url IS NOT NULL AND url <> \'\' LIMIT :limit'
            ),
            {"limit": _BATCH_SIZE},
        ).fetchall()
        if not rows:
            break

        by_user: dict[str, dict[str, str]] = {}
        for job_id, url, user_id, created_at in rows:
            domain = resolve_source(str(url))
            if not domain:
                continue
            cache_key = (str(user_id or ""), domain)
            site_id = inserted.get(cache_key)
            if site_id is None:
                site = bind.execute(
                    text(
                        "SELECT id FROM job.job_sources "
                        "WHERE user_id = :user_id AND normalized_domain = :domain LIMIT 1"
                    ),
                    {"user_id": user_id, "domain": domain},
                ).scalar()
                if site is None:
                    site_id = bind.execute(
                        text(
                            "INSERT INTO job.job_sources "
                            "(id, user_id, name, canonical_url, normalized_domain, is_active, created_at, updated_at) "
                            "VALUES (gen_random_uuid()::text, :user_id, :name, :canonical_url, :domain, 1, :created_at, :created_at) "
                            "RETURNING id"
                        ),
                        {
                            "user_id": user_id,
                            "name": display_name_for_domain(domain),
                            "canonical_url": f"https://{domain}",
                            "domain": domain,
                            "created_at": str(created_at or ""),
                        },
                    ).scalar()
                else:
                    site_id = str(site)
                inserted[cache_key] = site_id
            by_user.setdefault(str(user_id or ""), {})[str(job_id)] = site_id

        updated = 0
        for user_id, mapping in by_user.items():
            for job_id, site_id in mapping.items():
                updated += bind.execute(
                    text(
                        "UPDATE job.jobs SET source_site_id = :site_id "
                        "WHERE id = :job_id AND source_site_id IS NULL"
                    ),
                    {"site_id": site_id, "job_id": job_id},
                ).rowcount
        log.info(
            "job_009.backfill_batch", resolved_rows=len(rows), updated=updated
        )


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS job")
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("job_sources", schema="job"):
        op.create_table(
            "job_sources",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False, index=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("canonical_url", sa.String(), nullable=True),
            sa.Column("normalized_domain", sa.String(), nullable=False),
            sa.Column("is_active", sa.Integer(), nullable=False, default=1),
            sa.Column("created_at", sa.Text(), nullable=True),
            sa.Column("updated_at", sa.Text(), nullable=True),
            schema="job",
        )
        op.create_index(
            "uq_job_sources_user_domain",
            "job_sources",
            ["user_id", "normalized_domain"],
            unique=True,
            schema="job",
        )

    columns = {c["name"] for c in inspector.get_columns("jobs", schema="job")}
    if "source_site_id" not in columns:
        op.add_column(
            "jobs",
            sa.Column("source_site_id", sa.String(length=36), nullable=True),
            schema="job",
        )
        op.create_index(
            "idx_jobs_source_site_id", "jobs", ["source_site_id"], unique=False, schema="job"
        )

    inspector = sa.inspect(bind)
    _backfill_source_sites(bind)


def downgrade() -> None:
    op.drop_index("idx_jobs_source_site_id", table_name="jobs", schema="job")
    op.drop_column("jobs", "source_site_id", schema="job")
    op.drop_index("uq_job_sources_user_domain", table_name="job_sources", schema="job")
    op.drop_table("job_sources", schema="job")
