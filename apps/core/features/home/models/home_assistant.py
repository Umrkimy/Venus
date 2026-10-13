from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class HomeAssistantSetting(Base):
    """Where the owner's Home Assistant is and its access token (Settings, Home)."""

    __tablename__ = "home_assistant_settings"

    # One Home Assistant per Venus, so only the row with id 1.
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(200))
    # Fernet-encrypted long-lived access token; never sent back to the page.
    token_encrypted: Mapped[str] = mapped_column(Text)

    def __init__(self, id: int, url: str, token_encrypted: str) -> None:
        self.id = id
        self.url = url
        self.token_encrypted = token_encrypted
