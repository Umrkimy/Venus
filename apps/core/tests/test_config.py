import pytest

from pathlib import Path

from config import load_settings


def test_load_settings_reads_development_tokens(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_CORE_DEV_NODE_TOKEN=test-node-token\n"
        "VENUS_CORE_DEV_OWNER_TOKEN=test-owner-token\n",
    )

    settings = load_settings(env_file)

    assert settings.dev_node_token == "test-node-token"
    assert settings.dev_owner_token == "test-owner-token"


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
