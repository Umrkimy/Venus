from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.chat.schemas import ChatTurn
from features.conversations.models.conversation import Conversation, Message

TITLE_LENGTH = 60


class ConversationRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, first_message: str) -> UUID:
        conversation_id = uuid4()
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            session.add(
                Conversation(
                    id=conversation_id,
                    title=first_message.strip()[:TITLE_LENGTH],
                    created_at=now,
                    updated_at=now,
                ),
            )
            session.commit()
        return conversation_id

    def exists(self, conversation_id: UUID) -> bool:
        with Session(self.engine) as session:
            return session.get(Conversation, conversation_id) is not None

    def add_exchange(self, conversation_id: UUID, message: str, reply: str) -> None:
        # Both lines in one commit: a question is never saved without its answer.
        now = datetime.now(timezone.utc)
        with Session(self.engine) as session:
            session.add(Message(conversation_id, "user", message, now))
            session.add(Message(conversation_id, "assistant", reply, now))
            conversation = session.get(Conversation, conversation_id)
            conversation.updated_at = now
            session.commit()

    def recent_turns(self, conversation_id: UUID, limit: int = 10) -> list[ChatTurn]:
        with Session(self.engine) as session:
            newest_first = session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id.desc())
                .limit(limit)
            ).all()
        # ChatTurn caps content at 4000, the same cap the web used for history.
        return [
            ChatTurn(role=message.role, content=message.content[:4000])
            for message in reversed(newest_first)
        ]

    def list_all(self) -> list[Conversation]:
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(Conversation).order_by(Conversation.updated_at.desc())
                ).all()
            )

    def get(self, conversation_id: UUID) -> Conversation | None:
        with Session(self.engine) as session:
            return session.get(Conversation, conversation_id)

    def messages(self, conversation_id: UUID) -> list[Message]:
        with Session(self.engine) as session:
            return list(
                session.scalars(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.id)
                ).all()
            )
