from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class CharacterModel(Base):
    """The owner's own 3D Venus (.vrm file), kept out of git like the personality.

    No row = the web shows the template model shipped with Venus.
    """

    __tablename__ = "character_model"

    # One owner, one Venus: this table only ever holds the row with id 1.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The uploaded file's name, shown in Settings.
    name: Mapped[str] = mapped_column(String(200))
    size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # In the database, not a folder: private, and in the daily backups.
    data: Mapped[bytes] = mapped_column(LargeBinary)

    def __init__(self, id: int, name: str, size: int, uploaded_at: datetime, data: bytes) -> None:
        self.id = id
        self.name = name
        self.size = size
        self.uploaded_at = uploaded_at
        self.data = data
