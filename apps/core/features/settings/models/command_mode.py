from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class CommandModeSetting(Base):
    __tablename__ = "command_mode_settings"

    # Venus has one owner, so this table only ever holds the row with id 1.
    id: Mapped[int] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(20))

    def __init__(self, id: int, mode: str) -> None:
        self.id = id
        self.mode = mode
