"""add session details

Revision ID: a8e3d5f61c27
Revises: f2b7c4d91a36
Create Date: 2026-10-06 19:00:00.000000

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8e3d5f61c27'
down_revision: Union[str, Sequence[str], None] = 'f2b7c4d91a36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('owner_sessions', sa.Column('id', sa.Uuid(), nullable=True))
    op.add_column('owner_sessions', sa.Column('user_agent', sa.String(length=300), nullable=True))
    op.add_column('owner_sessions', sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
    # Existing logins keep working: give each one its own id.
    sessions = sa.table('owner_sessions', sa.column('token_hash', sa.String), sa.column('id', sa.Uuid))
    connection = op.get_bind()
    for (token_hash,) in connection.execute(sa.select(sessions.c.token_hash)).all():
        connection.execute(
            sessions.update().where(sessions.c.token_hash == token_hash).values(id=uuid4())
        )
    op.alter_column('owner_sessions', 'id', nullable=False)
    op.create_unique_constraint('uq_owner_sessions_id', 'owner_sessions', ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_owner_sessions_id', 'owner_sessions', type_='unique')
    op.drop_column('owner_sessions', 'last_seen_at')
    op.drop_column('owner_sessions', 'user_agent')
    op.drop_column('owner_sessions', 'id')
