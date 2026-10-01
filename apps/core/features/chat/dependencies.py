from typing import Annotated

from fastapi import Depends
from openai import AsyncOpenAI

from config import CoreSettings, get_settings
from features.chat.openai_provider import OpenAIProvider
from features.chat.provider import ChatProvider, FakeProvider


def get_chat_provider(
    settings: Annotated[CoreSettings, Depends(get_settings)],
) -> ChatProvider:
    if settings.llm_provider == "fake":
        return FakeProvider()
    if settings.llm_provider == "openai":
        if not settings.llm_api_key or not settings.llm_model:
            raise ValueError(
                "VENUS_CORE_LLM_API_KEY and VENUS_CORE_LLM_MODEL are required for openai",
            )
        return OpenAIProvider(
            AsyncOpenAI(api_key=settings.llm_api_key), settings.llm_model,
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
