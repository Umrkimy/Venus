from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class Personality(Base):
    __tablename__ = "personalities"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        id: UUID,
        name: str,
        text: str,
        active: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.name = name
        self.text = text
        self.active = active
        self.created_at = created_at
        self.updated_at = updated_at
