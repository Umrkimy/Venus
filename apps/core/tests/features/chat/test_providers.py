import pytest

from config import CoreSettings
from features.chat.dependencies import get_chat_provider


def test_unknown_llm_provider_is_rejected():
    settings = CoreSettings(
        dev_node_token="node",
        dev_owner_token="owner",
        database_url="sqlite+pysqlite://",
        llm_provider="nope",
    )

    with pytest.raises(ValueError):
        get_chat_provider(settings)


def test_openai_provider_needs_key_and_model():
    settings = CoreSettings(
        dev_node_token="node",
        dev_owner_token="owner",
        database_url="sqlite+pysqlite://",
        llm_provider="openai",
        llm_model="gpt-6-luna",
        llm_api_key="",
    )

    with pytest.raises(ValueError):
        get_chat_provider(settings)
