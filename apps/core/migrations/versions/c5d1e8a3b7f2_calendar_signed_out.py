"""calendar signed out

Revision ID: c5d1e8a3b7f2
Revises: b8e2f5a1c7d4
Create Date: 2026-10-26 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d1e8a3b7f2'
down_revision: Union[str, Sequence[str], None] = 'b8e2f5a1c7d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('calendar_accounts', sa.Column('signed_out_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('calendar_accounts', 'signed_out_at')
