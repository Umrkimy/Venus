"""create llm usage

Revision ID: e8f4a2c6d913
Revises: c7a2d8e4f519
Create Date: 2026-10-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f4a2c6d913'
down_revision: Union[str, Sequence[str], None] = 'c7a2d8e4f519'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('llm_usage',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('model', sa.String(length=100), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('cached_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_usage_created_at'), 'llm_usage', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_llm_usage_created_at'), table_name='llm_usage')
    op.drop_table('llm_usage')
