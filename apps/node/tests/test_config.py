import pytest
from pathlib import Path

from venus_node.config import load_settings


def test_load_settings_rejects_missing_device_id(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("VENUS_NODE_SPOTIFY_TARGET=spotify:\n")

    with pytest.raises(ValueError, match="VENUS_NODE_DEVICE_ID is required"):
        load_settings(env_file)


def test_load_settings_reads_private_node_values(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_SPOTIFY_TARGET=spotify: \n"
    )

    settings = load_settings(env_file)

    assert settings.device_id == "laptop-1"
    assert settings.spotify_target == "spotify:"


def test_load_settings_rejects_missing_spotify_target(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("VENUS_NODE_DEVICE_ID=laptop-1\n")

    with pytest.raises(ValueError, match="VENUS_NODE_SPOTIFY_TARGET is required"):
        load_settings(env_file)