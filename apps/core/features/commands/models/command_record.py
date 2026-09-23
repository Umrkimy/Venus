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
    application_id: Mapped[str] = mapped_column(String(100))
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
        application_id: str,
        expires_at: datetime,
        state: str = "awaiting_approval",
    ) -> None:
        self.command_id = command_id
        self.device_id = device_id
        self.application_id = application_id
        self.expires_at = expires_at
        self.state = state
        self.detail = None
        self.completed_at = None
