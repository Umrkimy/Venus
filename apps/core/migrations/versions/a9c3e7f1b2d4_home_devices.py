"""home devices and command payloads

Revision ID: a9c3e7f1b2d4
Revises: d4b8e1f6a2c3
Create Date: 2026-10-13 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9c3e7f1b2d4'
down_revision: Union[str, Sequence[str], None] = 'd4b8e1f6a2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'home_devices',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('kind', sa.String(length=10), nullable=False),
        sa.Column('address', sa.String(length=45), nullable=True),
        sa.Column('mac', sa.String(length=17), nullable=True),
        sa.Column('tuya_id', sa.String(length=64), nullable=True),
        sa.Column('local_key_encrypted', sa.Text(), nullable=True),
        sa.Column('tuya_version', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    # A home command remembers what to do (never the Tuya key) until you approve it.
    op.add_column('command_records', sa.Column('payload', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('command_records', 'payload')
    op.drop_table('home_devices')
