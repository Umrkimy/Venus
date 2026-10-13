"""calendar accounts (Google, Microsoft)

Revision ID: b1d5f8a2c4e6
Revises: a9c3e7f1b2d4
Create Date: 2026-10-13 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1d5f8a2c4e6'
down_revision: Union[str, Sequence[str], None] = 'a9c3e7f1b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'calendar_accounts',
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('client_id', sa.String(length=200), nullable=False),
        sa.Column('client_secret_encrypted', sa.Text(), nullable=False),
        sa.Column('refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('account_email', sa.String(length=320), nullable=True),
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('provider'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('calendar_accounts')
