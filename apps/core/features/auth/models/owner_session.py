from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class OwnerSession(Base):
    """One signed-in browser (PC, iPhone, Mac...)."""

    __tablename__ = "owner_sessions"

    token_hash: Mapped[str] = mapped_column(
        String(64),
        primary_key=True)
    # Safe to show in the web page, unlike the token hash.
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), unique=True)
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("owner_accounts.account_id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # What the browser said it is at login, e.g. "... iPhone ... Safari ...".
    user_agent: Mapped[str | None] = mapped_column(String(300))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        token_hash: str,
        id: UUID,
        account_id: UUID,
        created_at: datetime,
        expires_at: datetime,
        user_agent: str | None = None,
    ) -> None:
        self.token_hash = token_hash
        self.id = id
        self.account_id = account_id
        self.created_at = created_at
        self.expires_at = expires_at
        self.user_agent = user_agent
        self.last_seen_at = created_at
