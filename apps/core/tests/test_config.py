import pytest

from pathlib import Path

from config import FISH_MODEL, load_settings


def test_load_settings_reads_development_tokens(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_CORE_DEV_NODE_TOKEN=test-node-token\n"
        "VENUS_CORE_DEV_OWNER_TOKEN=test-owner-token\n"
        "VENUS_CORE_DATABASE_URL=postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus\n"
    )

    settings = load_settings(env_file)

    assert settings.dev_node_token == "test-node-token"
    assert settings.dev_owner_token == "test-owner-token"
    assert settings.database_url == (
        "postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus"
    )


def test_load_settings_reads_fish_voice(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_CORE_DEV_NODE_TOKEN=test-node-token\n"
        "VENUS_CORE_DEV_OWNER_TOKEN=test-owner-token\n"
        "VENUS_CORE_DATABASE_URL=postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus\n"
        "VENUS_CORE_FISH_API_KEY=fish-test\n"
        "VENUS_CORE_FISH_VOICE_ID=voice-123\n"
    )

    settings = load_settings(env_file)

    assert settings.fish_api_key == "fish-test"
    assert settings.fish_voice_id == "voice-123"
    # No model in .env: the free one.
    assert settings.fish_model == FISH_MODEL


def test_load_settings_rejects_missing_dev_node_token(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("")

    with pytest.raises(
        ValueError,
        match="VENUS_CORE_DEV_NODE_TOKEN is required",
    ):
        load_settings(env_file)


def test_load_settings_rejects_missing_dev_owner_token(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("VENUS_CORE_DEV_NODE_TOKEN=test-node-token\n")

    with pytest.raises(
        ValueError,
        match="VENUS_CORE_DEV_OWNER_TOKEN is required",
    ):
        load_settings(env_file)


def test_load_settings_rejects_missing_database_url(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_CORE_DEV_NODE_TOKEN=test-node-token\n"
        "VENUS_CORE_DEV_OWNER_TOKEN=test-owner-token\n"
    )

    with pytest.raises(
        ValueError,
        match="VENUS_CORE_DATABASE_URL is required",
    ):
        load_settings(env_file)

def test_environment_variable_wins_over_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_CORE_DEV_NODE_TOKEN=test-node-token\n"
        "VENUS_CORE_DEV_OWNER_TOKEN=test-owner-token\n"
        "VENUS_CORE_DATABASE_URL=postgresql+psycopg://venus:pw@127.0.0.1:5432/venus\n"
    )
    # Docker points Core at the postgres container this way.
    monkeypatch.setenv(
        "VENUS_CORE_DATABASE_URL",
        "postgresql+psycopg://venus:pw@postgres:5432/venus",
    )

    settings = load_settings(env_file)

    assert settings.database_url == (
        "postgresql+psycopg://venus:pw@postgres:5432/venus"
    )
    # Values only in the file still load.
    assert settings.dev_node_token == "test-node-token"


def test_environment_variables_work_without_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("VENUS_CORE_DEV_NODE_TOKEN", "env-node-token")
    monkeypatch.setenv("VENUS_CORE_DEV_OWNER_TOKEN", "env-owner-token")
    monkeypatch.setenv(
        "VENUS_CORE_DATABASE_URL",
        "postgresql+psycopg://venus:pw@postgres:5432/venus",
    )
    # Other variables are not settings.
    monkeypatch.setenv("CORE_URL", "http://core:9000")

    settings = load_settings(tmp_path / "missing.env")

    assert settings.dev_node_token == "env-node-token"
    assert settings.dev_owner_token == "env-owner-token"
