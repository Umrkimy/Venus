"""create time settings

Revision ID: e5a1c9d3b7f2
Revises: 4c7fcaed7749
Create Date: 2026-10-06 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5a1c9d3b7f2'
down_revision: Union[str, Sequence[str], None] = '4c7fcaed7749'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('time_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('time_zone', sa.String(length=64), nullable=False),
    sa.Column('country', sa.String(length=60), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('time_settings')
