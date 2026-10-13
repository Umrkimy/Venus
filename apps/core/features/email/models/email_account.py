from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class EmailAccount(Base):
    """One mailbox Venus can read and send from (Settings, Email)."""

    __tablename__ = "email_accounts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    address: Mapped[str] = mapped_column(String(320), unique=True)
    # The name people see on mail you send, and how Luna signs drafts.
    display_name: Mapped[str] = mapped_column(String(100))
    # imap (an app password), or google / microsoft (the sign-in from Settings, Calendar).
    kind: Mapped[str] = mapped_column(String(10), default="imap")
    # The rest is only for imap.
    imap_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imap_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    smtp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    smtp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # ssl (port 465/993), starttls (587), or none (only for a test server on this PC).
    smtp_security: Mapped[str | None] = mapped_column(String(10), nullable=True)
    imap_security: Mapped[str | None] = mapped_column(String(10), nullable=True)
    username: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # An app password, encrypted like the API keys; never sent back to the page.
    password_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(self, **fields) -> None:
        self.id = uuid4()
        for name, value in fields.items():
            setattr(self, name, value)
