from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends
from sqlalchemy.engine import Engine

from config import CoreSettings, get_settings
from features.calendar.repository import CalendarRepository
from features.calendar.service import Cached, CalendarService, SignIns
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
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
    settings_repository: Annotated[SettingsRepository, Depends(get_settings_repository)],
) -> CalendarService:
    saved = settings_repository.get_time()
    zone = ZoneInfo(saved.time_zone) if saved is not None and saved.time_zone else None
    return CalendarService(repository, settings.secret_key, cache=_cache, zone=zone)


def get_sign_ins() -> SignIns:
    return _sign_ins
