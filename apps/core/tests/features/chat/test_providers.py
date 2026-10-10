import pytest
from cryptography.fernet import Fernet

from config import CoreSettings
from features.chat.dependencies import get_chat_provider
from features.chat.openai_provider import OpenAIProvider
from features.chat.provider import FakeProvider
from features.settings.repository import SettingsRepository
from features.settings.secrets import encrypt_text
from tests.database import make_test_engine


def empty_repository() -> SettingsRepository:
    engine = make_test_engine()
    return SettingsRepository(engine)


def test_unknown_llm_provider_is_rejected():
    settings = CoreSettings(
        dev_node_token="node",
        dev_owner_token="owner",
        database_url="sqlite+pysqlite://",
        llm_provider="nope",
    )

    with pytest.raises(ValueError):
        get_chat_provider(settings, empty_repository())


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
        get_chat_provider(settings, empty_repository())


def test_chat_provider_uses_saved_llm_settings():
    secret_key = Fernet.generate_key().decode()
    settings = CoreSettings(
        dev_node_token="node",
        dev_owner_token="owner",
        database_url="sqlite+pysqlite://",
        llm_provider="fake",
        secret_key=secret_key,
    )
    repository = empty_repository()
    repository.set_llm(
        "openai", "gpt-6-luna", encrypt_text("sk-saved", secret_key),
    )

    provider = get_chat_provider(settings, repository)

    # The saved row beats .env's "fake", and its key was decrypted.
    assert isinstance(provider, OpenAIProvider)
    assert provider._client.api_key == "sk-saved"


def test_chat_provider_falls_back_to_env_without_saved_settings():
    settings = CoreSettings(
        dev_node_token="node",
        dev_owner_token="owner",
        database_url="sqlite+pysqlite://",
    )

    assert isinstance(get_chat_provider(settings, empty_repository()), FakeProvider)
