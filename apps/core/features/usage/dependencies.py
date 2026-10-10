from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.usage.repository import UsageRepository
from storage.database import get_database_engine


def get_usage_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> UsageRepository:
    return UsageRepository(engine)
