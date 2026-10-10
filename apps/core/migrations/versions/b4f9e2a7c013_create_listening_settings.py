"""create listening settings

Revision ID: b4f9e2a7c013
Revises: a8e3d5f61c27
Create Date: 2026-10-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4f9e2a7c013'
down_revision: Union[str, Sequence[str], None] = 'a8e3d5f61c27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('listening_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('end_pause_ms', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('listening_settings')
