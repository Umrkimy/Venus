from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class TimeSetting(Base):
    __tablename__ = "time_settings"

    # One owner, one home: this table only ever holds the row with id 1.
    id: Mapped[int] = mapped_column(primary_key=True)
    # An IANA time zone name, for example "Asia/Kuala_Lumpur".
    time_zone: Mapped[str] = mapped_column(String(64))
    country: Mapped[str] = mapped_column(String(60))

    def __init__(self, id: int, time_zone: str, country: str) -> None:
        self.id = id
        self.time_zone = time_zone
        self.country = country
