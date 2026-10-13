"""venus's own calendar events

Revision ID: e6a2c8d4f1b9
Revises: d3f8b6a1e9c4
Create Date: 2026-10-14 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6a2c8d4f1b9'
down_revision: Union[str, Sequence[str], None] = 'd3f8b6a1e9c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'venus_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('all_day', sa.Boolean(), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_venus_events_start'), 'venus_events', ['start'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_venus_events_start'), table_name='venus_events')
    op.drop_table('venus_events')
