from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Moves forward with every message, so the newest chat sorts first.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Empty means the chat isn't in a project.
    project_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id"),
        index=True,
        default=None,
    )
    # Empty means active; a time means the owner archived the chat then.
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )

    def __init__(
        self,
        id: UUID,
        title: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self.id = id
        self.title = title
        self.created_at = created_at
        self.updated_at = updated_at


class Message(Base):
    __tablename__ = "messages"

    # A counting number keeps messages in order even when two share a timestamp.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        created_at: datetime,
    ) -> None:
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.created_at = created_at
