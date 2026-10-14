"""character places

Revision ID: b8e2f5a1c7d4
Revises: a7d3f1c9e5b2
Create Date: 2026-10-14 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e2f5a1c7d4'
down_revision: Union[str, Sequence[str], None] = 'a7d3f1c9e5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('character_place',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('character_place')
