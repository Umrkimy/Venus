from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class SiteShortcut(Base):
    __tablename__ = "site_shortcuts"

    keyword: Mapped[str] = mapped_column(String(50), primary_key=True)
    label: Mapped[str] = mapped_column(String(100))
    home_url: Mapped[str] = mapped_column(String(2083))
    # None means the site can only be opened, not searched.
    search_url: Mapped[str | None] = mapped_column(String(2083))

    def __init__(
        self,
        keyword: str,
        label: str,
        home_url: str,
        search_url: str | None,
    ) -> None:
        self.keyword = keyword
        self.label = label
        self.home_url = home_url
        self.search_url = search_url
