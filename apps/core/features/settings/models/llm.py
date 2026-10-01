from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class LlmSetting(Base):
    __tablename__ = "llm_settings"

    # Venus has one owner, so this table only ever holds the row with id 1.
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(100))
    # Fernet-encrypted API key; None means "no key saved".
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __init__(
        self,
        id: int,
        provider: str,
        model: str,
        api_key_encrypted: str | None,
    ) -> None:
        self.id = id
        self.provider = provider
        self.model = model
        self.api_key_encrypted = api_key_encrypted
