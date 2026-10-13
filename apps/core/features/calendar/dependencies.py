from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from config import CoreSettings, get_settings
from features.calendar.repository import CalendarRepository
from features.calendar.service import Cached, CalendarService, SignIns
from storage.database import get_database_engine

# One per Core process: the 5-minute event cache and the sign-ins in progress.
_cache = Cached()
_sign_ins = SignIns()


def get_calendar_repository(
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> CalendarRepository:
    return CalendarRepository(engine)


def get_calendar_service(
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
) -> CalendarService:
    return CalendarService(repository, settings.secret_key, cache=_cache)


def get_sign_ins() -> SignIns:
    return _sign_ins
