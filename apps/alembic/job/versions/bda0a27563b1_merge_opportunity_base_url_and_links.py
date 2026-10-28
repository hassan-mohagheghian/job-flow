"""merge opportunity base_url and links

Revision ID: bda0a27563b1
Revises: job_010, opportunity_004
Create Date: 2026-10-28 11:42:30.473025

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bda0a27563b1'
down_revision: Union[str, None] = ('job_010', 'opportunity_004')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
