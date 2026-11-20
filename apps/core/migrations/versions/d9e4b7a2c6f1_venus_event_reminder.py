"""venus event reminder

Revision ID: d9e4b7a2c6f1
Revises: c5d1e8a3b7f2
Create Date: 2026-11-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9e4b7a2c6f1'
down_revision: Union[str, Sequence[str], None] = 'c5d1e8a3b7f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('venus_events', sa.Column('reminder', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('venus_events', 'reminder')
