from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.conversations.repository import ConversationRepository
from storage.database import get_database_engine


def get_conversation_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> ConversationRepository:
    return ConversationRepository(engine)
