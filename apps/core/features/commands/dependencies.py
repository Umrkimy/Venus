from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.commands.repository import CommandRecordRepository
from storage.database import get_database_engine


def get_command_record_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> CommandRecordRepository:
    return CommandRecordRepository(engine)
