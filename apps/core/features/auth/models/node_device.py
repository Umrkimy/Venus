from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base

MAX_DEVICE_ID_LENGTH = 100


class NodeDevice(Base):
    """One PC (Node) allowed to connect, with its own token.

    Only the token's SHA-256 hash is stored. device_id stays empty until the
    first Node connects with the token; after that the token only works for
    that device. The main device (from the .env token) can't be revoked from
    the web; changing the .env token replaces it.
    """

    __tablename__ = "node_devices"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    device_id: Mapped[str | None] = mapped_column(String(MAX_DEVICE_ID_LENGTH), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)

    def __init__(
        self,
        id: UUID,
        name: str,
        token_hash: str,
        created_at: datetime,
        is_main: bool = False,
    ) -> None:
        self.id = id
        self.name = name
        self.token_hash = token_hash
        self.device_id = None
        self.created_at = created_at
        self.last_seen_at = None
        self.revoked_at = None
        self.is_main = is_main
