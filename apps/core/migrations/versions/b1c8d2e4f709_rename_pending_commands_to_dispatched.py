"""rename pending command records to dispatched

Revision ID: b1c8d2e4f709
Revises: 6ec5836931d0
Create Date: 2026-09-22

"""

from typing import Sequence, Union

from alembic import op


revision: str = "b1c8d2e4f709"
down_revision: Union[str, Sequence[str], None] = "6ec5836931d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE command_records SET state = 'dispatched' WHERE state = 'pending'",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE command_records SET state = 'pending' WHERE state = 'dispatched'",
    )
