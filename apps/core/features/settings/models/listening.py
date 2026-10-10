from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class ListeningSetting(Base):
    __tablename__ = "listening_settings"

    # One owner: this table only ever holds the row with id 1.
    id: Mapped[int] = mapped_column(primary_key=True)
    # How long Venus waits after you stop talking before your sentence is sent.
    end_pause_ms: Mapped[int]
    # The PC mic's name as Windows lists it; empty = the Windows default mic.
    mic: Mapped[str] = mapped_column(String(200), server_default="")

    def __init__(self, id: int, end_pause_ms: int, mic: str = "") -> None:
        self.id = id
        self.end_pause_ms = end_pause_ms
        self.mic = mic
