"""home assistant settings and entity ids

Revision ID: c7e2a9f4d1b8
Revises: b1d5f8a2c4e6
Create Date: 2026-10-13 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e2a9f4d1b8'
down_revision: Union[str, Sequence[str], None] = 'b1d5f8a2c4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'home_assistant_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(length=200), nullable=False),
        sa.Column('token_encrypted', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    # A device imported from Home Assistant, like light.bedroom.
    op.add_column('home_devices', sa.Column('ha_entity_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('home_devices', 'ha_entity_id')
    op.drop_table('home_assistant_settings')
