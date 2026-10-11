"""keep several character models, one active

Revision ID: d4b8e1f6a2c3
Revises: c7e2d5a8f914
Create Date: 2026-10-11 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4b8e1f6a2c3'
down_revision: Union[str, Sequence[str], None] = 'c7e2d5a8f914'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'character_model',
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Before this, the one row there was always the model in use.
    op.execute("UPDATE character_model SET active = true")
    if op.get_bind().dialect.name == 'postgresql':
        # That row was saved with id 1 by hand, so the id counter never moved:
        # without this the next upload would try id 1 again.
        op.execute(
            "SELECT setval(pg_get_serial_sequence('character_model', 'id'), "
            "COALESCE(MAX(id), 0) + 1, false) FROM character_model"
        )


def downgrade() -> None:
    """Downgrade schema."""
    # The old code knows one model, saved as id 1: keep only the one in use.
    op.execute("DELETE FROM character_model WHERE active = false")
    op.execute("UPDATE character_model SET id = 1")
    op.drop_column('character_model', 'active')
