from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class OwnerAccount(Base):
    __tablename__ = "owner_accounts"

    account_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True)
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        account_id: UUID,
        username: str,
        password_hash: str,
        created_at: datetime,
    ) -> None:
        self.account_id = account_id
        self.username = username
        self.password_hash = password_hash
        self.created_at = created_at