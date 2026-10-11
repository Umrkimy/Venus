from datetime import datetime

from sqlalchemy import DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class CharacterAnimation(Base):
    """A move the owner uploaded for 3D Venus (.vrma file), kept out of git like the model.

    Free packs (pixiv's VRMA pack, BOOTH) don't allow sharing the files, so each
    owner downloads their own. No rows = Venus only does her coded moves.
    """

    __tablename__ = "character_animation"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # When it plays: "idle", "hello", "listening", "thinking" or "talking".
    use: Mapped[str] = mapped_column(String(20))
    size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data: Mapped[bytes] = mapped_column(LargeBinary)

    def __init__(self, name: str, use: str, size: int, uploaded_at: datetime, data: bytes) -> None:
        self.name = name
        self.use = use
        self.size = size
        self.uploaded_at = uploaded_at
        self.data = data
