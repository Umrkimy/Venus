from typing import Annotated

from fastapi import Depends

from config import CoreSettings, get_settings
from features.chat.provider import ChatProvider, FakeProvider


def get_chat_provider(
    settings: Annotated[CoreSettings, Depends(get_settings)],
) -> ChatProvider:
    if settings.llm_provider == "fake":
        return FakeProvider()
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
