"""ics calendars (links and uploaded files)

Revision ID: d3f8b6a1e9c4
Revises: c7e2a9f4d1b8
Create Date: 2026-10-14 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f8b6a1e9c4'
down_revision: Union[str, Sequence[str], None] = 'c7e2a9f4d1b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ics_calendars',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('url_encrypted', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('ics_calendars')
