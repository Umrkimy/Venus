from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from config import CoreSettings, get_settings
from features.auth.dependencies import require_owner
from features.settings.dependencies import get_settings_repository
from features.settings.models.llm import LlmSetting
from features.settings.models.time import TimeSetting
from features.settings.models.voice import VoiceSetting
from features.settings.repository import SettingsRepository
from features.settings.schemas import (
    CommandModeRequest,
    ListeningSettingsRequest,
    LlmSettingsRequest,
    TimeSettingsRequest,
    VoiceSettingsRequest,
)
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


def encrypt_key(api_key: str | None, settings: CoreSettings) -> str | None:
    """A new key, encrypted for the database; None keeps the saved one."""
    if not api_key:
        return None
    if not settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Set VENUS_CORE_SECRET_KEY in Core's .env first",
        )
    return encrypt_text(api_key, settings.secret_key)


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
    api_key_encrypted = encrypt_key(request.api_key, settings)
    settings_repository.set_llm(request.provider, request.model, api_key_encrypted)
    return llm_settings_json(settings_repository.get_llm(), settings)


def voice_settings_json(saved: VoiceSetting | None, settings: CoreSettings) -> dict:
    # Like the LLM key: only whether a Fish key is set, never the key.
    if saved is None:
        return {
            "voice_id": settings.fish_voice_id,
            "model": settings.fish_model,
            "has_key": bool(settings.fish_api_key),
        }
    return {
        "voice_id": saved.voice_id,
        "model": saved.model,
        "has_key": bool(saved.api_key_encrypted or settings.fish_api_key),
    }


@router.get("/voice", dependencies=[Depends(require_owner)])
def get_voice_settings(
    settings: Annotated[CoreSettings, Depends(get_settings)],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    return voice_settings_json(settings_repository.get_voice(), settings)


@router.put("/voice", dependencies=[Depends(require_owner)])
def set_voice_settings(
    request: VoiceSettingsRequest,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    api_key_encrypted = encrypt_key(request.api_key, settings)
    settings_repository.set_voice(
        request.voice_id.strip(), request.model, api_key_encrypted,
    )
    return voice_settings_json(settings_repository.get_voice(), settings)


def time_settings_json(saved: TimeSetting | None) -> dict:
    # Nothing saved yet: the web suggests the browser's time zone.
    if saved is None:
        return {"time_zone": None, "country": ""}
    return {"time_zone": saved.time_zone, "country": saved.country}


@router.get("/time", dependencies=[Depends(require_owner)])
def get_time_settings(
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    return time_settings_json(settings_repository.get_time())


@router.put("/time", dependencies=[Depends(require_owner)])
def set_time_settings(
    request: TimeSettingsRequest,
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    settings_repository.set_time(request.time_zone, request.country.strip())
    return time_settings_json(settings_repository.get_time())


def listening_json(settings_repository: SettingsRepository) -> dict:
    saved = settings_repository.get_listening()
    return {"end_pause_ms": saved.end_pause_ms, "mic": saved.mic}


@router.get("/listening", dependencies=[Depends(require_owner)])
def get_listening_settings(
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    return listening_json(settings_repository)


@router.put("/listening", dependencies=[Depends(require_owner)])
def set_listening_settings(
    request: ListeningSettingsRequest,
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
):
    settings_repository.set_listening(request.end_pause_ms, request.mic)
    return listening_json(settings_repository)
