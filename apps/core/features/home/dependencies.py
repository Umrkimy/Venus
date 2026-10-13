from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.home.repository import HomeDeviceRepository
from storage.database import get_database_engine


def get_home_device_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> HomeDeviceRepository:
    return HomeDeviceRepository(engine)
