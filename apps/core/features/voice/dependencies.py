from typing import Annotated

from fastapi import Depends, HTTPException, status
from openai import AsyncOpenAI

from config import CoreSettings, get_settings
from features.chat.dependencies import llm_choice
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.voice.speaker import FishSpeaker, Speaker
from features.voice.transcriber import OpenAITranscriber, Transcriber


def get_transcriber(
    settings: Annotated[CoreSettings, Depends(get_settings)],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
) -> Transcriber:
    # Same key as chat: saved from the web first, otherwise .env.
    provider, _, api_key = llm_choice(settings, settings_repository)
    if provider != "openai" or not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice needs an OpenAI API key",
        )
    return OpenAITranscriber(AsyncOpenAI(api_key=api_key))


def get_speaker(
    settings: Annotated[CoreSettings, Depends(get_settings)],
) -> Speaker:
    # Luna's voice lives on fish.audio; key and voice id come from .env.
    if not settings.fish_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice reply needs a Fish Audio key",
        )
    return FishSpeaker(
        settings.fish_api_key, settings.fish_voice_id, settings.fish_model,
    )
