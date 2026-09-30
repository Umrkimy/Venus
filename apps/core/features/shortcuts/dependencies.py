from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.shortcuts.repository import ShortcutRepository
from storage.database import get_database_engine


def get_shortcut_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> ShortcutRepository:
    return ShortcutRepository(engine)
