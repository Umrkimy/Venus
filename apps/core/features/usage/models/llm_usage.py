from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class LlmUsage(Base):
    """One paid call to the AI provider: what it used, not what it cost.

    Cost is worked out when you look (prices.py), so fixing a price there
    fixes old rows too.
    """

    __tablename__ = "llm_usage"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # "chat" or "transcribe"
    model: Mapped[str] = mapped_column(String(100))
    # All input tokens; cached_tokens is the part of them the provider had
    # seen before, which costs less.
    input_tokens: Mapped[int] = mapped_column(Integer)
    cached_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)

    def __init__(
        self,
        id: UUID,
        created_at: datetime,
        kind: str,
        model: str,
        input_tokens: int,
        cached_tokens: int,
        output_tokens: int,
    ) -> None:
        self.id = id
        self.created_at = created_at
        self.kind = kind
        self.model = model
        self.input_tokens = input_tokens
        self.cached_tokens = cached_tokens
        self.output_tokens = output_tokens
