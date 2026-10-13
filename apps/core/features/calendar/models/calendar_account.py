from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class CalendarAccount(Base):
    """One calendar provider: your own OAuth app (client) and, once connected, its sign-in."""

    __tablename__ = "calendar_accounts"

    # google or microsoft
    provider: Mapped[str] = mapped_column(String(20), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(200))
    # Encrypted like the API keys; never sent back to the page.
    client_secret_encrypted: Mapped[str] = mapped_column(Text)
    # Lets Venus read the calendar without you signing in again. Encrypted.
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __init__(self, provider: str, client_id: str, client_secret_encrypted: str) -> None:
        self.provider = provider
        self.client_id = client_id
        self.client_secret_encrypted = client_secret_encrypted
        self.refresh_token_encrypted = None
        self.account_email = None
        self.connected_at = None
