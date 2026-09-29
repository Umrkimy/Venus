"""widen command application_id

Revision ID: 5bd3cdcb7e9b
Revises: dcd787205087
Create Date: 2026-09-30 02:05:02.572056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bd3cdcb7e9b'
down_revision: Union[str, Sequence[str], None] = 'dcd787205087'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Some Start menu AppIDs are longer than 100 characters
    op.alter_column(
        "command_records",
        "application_id",
        existing_type=sa.String(length=100),
        type_=sa.String(length=512),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Fails if a stored application_id is longer than 100 characters
    op.alter_column(
        "command_records",
        "application_id",
        existing_type=sa.String(length=512),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
