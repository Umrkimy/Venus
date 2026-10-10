from dataclasses import asdict
from datetime import datetime, timezone
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends

from features.auth.dependencies import require_owner
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.usage.dependencies import get_usage_repository
from features.usage.repository import UsageRepository


router = APIRouter(prefix="/usage", dependencies=[Depends(require_owner)])


def period_starts(now_utc: datetime, time_zone: str | None) -> tuple[datetime, datetime]:
    """Start of the owner's today and this month, as UTC moments.

    "Today" is the owner's day, not Core's: Core runs on UTC in Docker.
    """
    local = now_utc.astimezone(ZoneInfo(time_zone) if time_zone else timezone.utc)
    day_start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    return day_start.astimezone(timezone.utc), month_start.astimezone(timezone.utc)


@router.get("")
def get_usage(
    usage: Annotated[UsageRepository, Depends(get_usage_repository)],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    saved_time = settings_repository.get_time()
    today, month = period_starts(
        datetime.now(timezone.utc),
        saved_time.time_zone if saved_time is not None else None,
    )
    return {
        "today": asdict(usage.total_since(today)),
        "month": asdict(usage.total_since(month)),
        "all_time": asdict(usage.total_since(None)),
    }
