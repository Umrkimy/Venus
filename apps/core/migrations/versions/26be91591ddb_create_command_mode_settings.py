"""create command mode settings

Revision ID: 26be91591ddb
Revises: 5bd3cdcb7e9b
Create Date: 2026-09-30 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26be91591ddb'
down_revision: Union[str, Sequence[str], None] = '5bd3cdcb7e9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # No row means the default mode, "confirm".
    op.create_table(
        "command_mode_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("command_mode_settings")
