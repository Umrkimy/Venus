from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    text: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(self, id: UUID, text: str, created_at: datetime) -> None:
        self.id = id
        self.text = text
        self.created_at = created_at
