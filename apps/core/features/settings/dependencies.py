from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.settings.repository import SettingsRepository
from storage.database import get_database_engine


def get_settings_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> SettingsRepository:
    return SettingsRepository(engine)
