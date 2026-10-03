from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class VoiceSetting(Base):
    __tablename__ = "voice_settings"

    # One owner, one voice: this table only ever holds the row with id 1.
    id: Mapped[int] = mapped_column(primary_key=True)
    # The voice model's id on fish.audio; empty lets Fish pick a default voice.
    voice_id: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(40))
    # Fernet-encrypted Fish Audio key; None means "no key saved".
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __init__(
        self,
        id: int,
        voice_id: str,
        model: str,
        api_key_encrypted: str | None,
    ) -> None:
        self.id = id
        self.voice_id = voice_id
        self.model = model
        self.api_key_encrypted = api_key_encrypted
