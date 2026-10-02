from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.projects.repository import ProjectRepository
from storage.database import get_database_engine


def get_project_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> ProjectRepository:
    return ProjectRepository(engine)
