"""add workflow_progress to processing_executions

JSON workflow step/progress payload surfaced by the processing queue service
and the executions API (``workflow_progress`` on the execution entity).

Revision ID: 807af848eab4
Revises: job_009
Create Date: 2026-10-18 17:59:08.102315

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '807af848eab4'
down_revision: Union[str, None] = 'job_009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "processing_executions"
_SCHEMA = "processing"
_COLUMN = "workflow_progress"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS processing")
    bind = op.get_bind()
    insp = inspect(bind)
    if insp.has_table(_TABLE, schema=_SCHEMA):
        cols = {c["name"] for c in insp.get_columns(_TABLE, schema=_SCHEMA)}
        if _COLUMN not in cols:
            op.add_column(
                _TABLE,
                sa.Column(_COLUMN, sa.Text, nullable=True),
                schema=_SCHEMA,
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if insp.has_table(_TABLE, schema=_SCHEMA):
        cols = {c["name"] for c in insp.get_columns(_TABLE, schema=_SCHEMA)}
        if _COLUMN in cols:
            op.drop_column(_TABLE, _COLUMN, schema=_SCHEMA)
