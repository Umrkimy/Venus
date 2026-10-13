"""mail through the Google/Microsoft sign-in

Revision ID: a7d3f1c9e5b2
Revises: f4b9d2e7a6c1
Create Date: 2026-10-14 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d3f1c9e5b2'
down_revision: Union[str, Sequence[str], None] = 'f4b9d2e7a6c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

IMAP_ONLY = [
    ('imap_host', sa.String(length=255)),
    ('imap_port', sa.Integer()),
    ('smtp_host', sa.String(length=255)),
    ('smtp_port', sa.Integer()),
    ('smtp_security', sa.String(length=10)),
    ('imap_security', sa.String(length=10)),
    ('username', sa.String(length=320)),
    ('password_encrypted', sa.Text()),
]


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('calendar_accounts', sa.Column('mail', sa.Boolean(), server_default=sa.false(), nullable=False))
    for name, kind in IMAP_ONLY:
        op.alter_column('email_accounts', name, existing_type=kind, nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM email_accounts WHERE kind <> 'imap'")
    for name, kind in IMAP_ONLY:
        op.alter_column('email_accounts', name, existing_type=kind, nullable=False)
    op.drop_column('calendar_accounts', 'mail')
