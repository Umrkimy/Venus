from typing import Annotated

from fastapi import APIRouter, Depends

from features.auth.dependencies import require_owner
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.settings.schemas import CommandModeRequest


router = APIRouter(prefix="/settings")


@router.get("/mode", dependencies=[Depends(require_owner)])
def get_command_mode(
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    return {"mode": settings_repository.get_mode()}


@router.put("/mode", dependencies=[Depends(require_owner)])
def set_command_mode(
    request: CommandModeRequest,
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    settings_repository.set_mode(request.mode)
    return {"mode": request.mode}