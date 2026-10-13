"""email accounts (IMAP/SMTP)

Revision ID: f4b9d2e7a6c1
Revises: e6a2c8d4f1b9
Create Date: 2026-10-14 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4b9d2e7a6c1'
down_revision: Union[str, Sequence[str], None] = 'e6a2c8d4f1b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'email_accounts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('address', sa.String(length=320), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('kind', sa.String(length=10), nullable=False),
        sa.Column('imap_host', sa.String(length=255), nullable=False),
        sa.Column('imap_port', sa.Integer(), nullable=False),
        sa.Column('smtp_host', sa.String(length=255), nullable=False),
        sa.Column('smtp_port', sa.Integer(), nullable=False),
        sa.Column('smtp_security', sa.String(length=10), nullable=False),
        sa.Column('imap_security', sa.String(length=10), nullable=False),
        sa.Column('username', sa.String(length=320), nullable=False),
        sa.Column('password_encrypted', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('address'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('email_accounts')
