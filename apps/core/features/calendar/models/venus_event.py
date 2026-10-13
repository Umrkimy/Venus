from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class VenusEvent(Base):
    """An event on Venus's own calendar (made on the Calendar page)."""

    __tablename__ = "venus_events"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200))
    # Timezone-aware; all-day events start at midnight UTC of their first day.
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    location: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        title: str,
        start: datetime,
        end: datetime,
        created_at: datetime,
        all_day: bool = False,
        location: str = "",
        notes: str = "",
    ) -> None:
        self.id = uuid4()
        self.title = title
        self.start = start
        self.end = end
        self.all_day = all_day
        self.location = location
        self.notes = notes
        self.created_at = created_at
