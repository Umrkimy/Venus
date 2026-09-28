from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class OwnerSession(Base):
    __tablename__ = "owner_sessions"

    token_hash: Mapped[str] = mapped_column(
        String(64),
        primary_key=True)
    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("owner_accounts.account_id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        token_hash: str,
        account_id: UUID,
        created_at: datetime,
        expires_at: datetime,
    ) -> None:
        self.token_hash = token_hash
        self.account_id = account_id
        self.created_at = created_at
        self.expires_at = expires_at