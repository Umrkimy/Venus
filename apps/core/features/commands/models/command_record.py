from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class CommandRecord(Base):
    __tablename__ = "command_records"

    command_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    device_id: Mapped[str] = mapped_column(String(100))
    application_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    kind: Mapped[str] = mapped_column(
        String(20),
        server_default="open_application",
    )
    # 2083 is Pydantic HttpUrl's max length; raise both together.
    url: Mapped[str | None] = mapped_column(String(2083), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(20))
    detail: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __init__(
        self,
        command_id: UUID,
        device_id: str,
        application_id: str | None,
        expires_at: datetime,
        state: str = "awaiting_approval",
        kind: str = "open_application",
        url: str | None = None,
    ) -> None:
        self.command_id = command_id
        self.device_id = device_id
        self.application_id = application_id
        self.expires_at = expires_at
        self.state = state
        self.kind = kind
        self.url = url
        self.detail = None
        self.completed_at = None
