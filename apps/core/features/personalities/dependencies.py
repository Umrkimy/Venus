from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.personalities.repository import PersonalityRepository
from storage.database import get_database_engine


def get_personality_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> PersonalityRepository:
    return PersonalityRepository(engine)
