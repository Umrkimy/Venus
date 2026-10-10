"""add mic to listening settings

Revision ID: c7a2d8e4f519
Revises: b4f9e2a7c013
Create Date: 2026-10-10 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a2d8e4f519'
down_revision: Union[str, Sequence[str], None] = 'b4f9e2a7c013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('listening_settings', sa.Column('mic', sa.String(length=200), server_default='', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('listening_settings', 'mic')
