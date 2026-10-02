from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.memories.repository import MemoryRepository
from storage.database import get_database_engine


def get_memory_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> MemoryRepository:
    return MemoryRepository(engine)
