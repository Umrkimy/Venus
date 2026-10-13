from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class IcsCalendar(Base):
    """A calendar from an .ics link or file, like a uni timetable."""

    __tablename__ = "ics_calendars"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    # What it's called in Settings, Calendar: "Uni timetable".
    name: Mapped[str] = mapped_column(String(40), unique=True)
    # A link Venus re-reads. Encrypted: these links often carry a private key.
    url_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Or an uploaded file's text, kept as it was.
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        name: str,
        created_at: datetime,
        url_encrypted: str | None = None,
        content: str | None = None,
    ) -> None:
        self.id = uuid4()
        self.name = name
        self.url_encrypted = url_encrypted
        self.content = content
        self.created_at = created_at
