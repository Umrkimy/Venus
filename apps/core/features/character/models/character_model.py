from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class CharacterModel(Base):
    """A 3D Venus the owner uploaded (.vrm file), kept out of git like the personality.

    Several can be kept; at most one is in use. None in use = the web shows the
    template model shipped with Venus.
    """

    __tablename__ = "character_model"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The uploaded file's name, shown in Settings.
    name: Mapped[str] = mapped_column(String(200))
    size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # The one Venus shows. Switching only moves this flag, so nothing is lost.
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    # In the database, not a folder: private, and in the daily backups.
    data: Mapped[bytes] = mapped_column(LargeBinary)

    def __init__(self, name: str, size: int, uploaded_at: datetime, data: bytes, active: bool) -> None:
        self.name = name
        self.size = size
        self.uploaded_at = uploaded_at
        self.data = data
        self.active = active
