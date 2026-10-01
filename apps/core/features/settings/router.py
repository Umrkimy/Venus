from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from config import CoreSettings, get_settings
from features.auth.dependencies import require_owner
from features.settings.dependencies import get_settings_repository
from features.settings.models.llm import LlmSetting
from features.settings.repository import SettingsRepository
from features.settings.schemas import CommandModeRequest, LlmSettingsRequest
from features.settings.secrets import encrypt_text


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


def llm_settings_json(saved: LlmSetting | None, settings: CoreSettings) -> dict:
    # The key itself never leaves Core: only whether one is set.
    if saved is None:
        return {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "has_key": bool(settings.llm_api_key),
        }
    return {
        "provider": saved.provider,
        "model": saved.model,
        "has_key": bool(saved.api_key_encrypted or settings.llm_api_key),
    }


@router.get("/llm", dependencies=[Depends(require_owner)])
def get_llm_settings(
    settings: Annotated[CoreSettings, Depends(get_settings)],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    return llm_settings_json(settings_repository.get_llm(), settings)


@router.put("/llm", dependencies=[Depends(require_owner)])
def set_llm_settings(
    request: LlmSettingsRequest,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    api_key_encrypted = None
    if request.api_key:
        if not settings.secret_key:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Set VENUS_CORE_SECRET_KEY in Core's .env first",
            )
        api_key_encrypted = encrypt_text(request.api_key, settings.secret_key)

    settings_repository.set_llm(request.provider, request.model, api_key_encrypted)
    return llm_settings_json(settings_repository.get_llm(), settings)
