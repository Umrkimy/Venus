from typing import Annotated

from fastapi import Depends
from openai import AsyncOpenAI

from config import CoreSettings, get_settings
from features.chat.openai_provider import OpenAIProvider
from features.chat.provider import ChatProvider, FakeProvider
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.settings.secrets import decrypt_text


def get_chat_provider(
    settings: Annotated[CoreSettings, Depends(get_settings)],
    settings_repository: Annotated[
        SettingsRepository,
        Depends(get_settings_repository),
    ],
) -> ChatProvider:
    # Settings saved from the web win; otherwise .env, like before.
    saved = settings_repository.get_llm()
    if saved is None:
        provider, model, api_key = (
            settings.llm_provider, settings.llm_model, settings.llm_api_key,
        )
    else:
        provider, model = saved.provider, saved.model
        api_key = settings.llm_api_key
        if saved.api_key_encrypted:
            api_key = decrypt_text(saved.api_key_encrypted, settings.secret_key)

    if provider == "fake":
        return FakeProvider()
    if provider == "openai":
        if not api_key or not model:
            raise ValueError("An API key and a model are required for openai")
        return OpenAIProvider(AsyncOpenAI(api_key=api_key), model)
    raise ValueError(f"Unknown LLM provider: {provider}")
