from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from config import get_settings


def create_database_engine(database_url: str) -> Engine:
    return create_engine(database_url)


@lru_cache
def get_database_engine() -> Engine:
    return create_database_engine(get_settings().database_url)
