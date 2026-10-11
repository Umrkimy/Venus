from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.character.repository import AnimationRepository, CharacterRepository
from storage.database import get_database_engine


def get_character_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> CharacterRepository:
    return CharacterRepository(engine)


def get_animation_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> AnimationRepository:
    return AnimationRepository(engine)
