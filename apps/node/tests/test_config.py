import pytest
from pathlib import Path

from venus_node.config import load_settings


def test_load_settings_rejects_missing_device_id(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text("VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n")

    with pytest.raises(ValueError, match="VENUS_NODE_DEVICE_ID is required"):
        load_settings(env_file)


def test_load_settings_reads_private_node_values(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
    )

    settings = load_settings(env_file)

    assert settings.device_id == "laptop-1"
    assert settings.core_dev_token == "test-node-token"
    assert settings.core_url == "ws://core.test/nodes/connect"


def test_load_settings_rejects_missing_core_dev_token(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
    )

    with pytest.raises(
        ValueError,
        match="VENUS_NODE_CORE_DEV_TOKEN is required",
    ):
        load_settings(env_file)


def test_load_settings_rejects_missing_core_url(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
    )

    with pytest.raises(
        ValueError,
        match="VENUS_NODE_CORE_URL is required",
    ):
        load_settings(env_file)


def test_load_settings_defaults_real_actions_to_false(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
    )

    settings = load_settings(env_file)

    assert settings.real_actions is False


def test_load_settings_reads_real_actions_true(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
        "VENUS_NODE_REAL_ACTIONS=true\n"
    )

    settings = load_settings(env_file)

    assert settings.real_actions is True


def test_load_settings_rejects_invalid_real_actions(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
        "VENUS_NODE_REAL_ACTIONS=invalid_value\n"
    )

    with pytest.raises(
        ValueError,
        match="VENUS_NODE_REAL_ACTIONS must be true or false",
    ):
        load_settings(env_file)


NODE_VALUES = (
    "VENUS_NODE_DEVICE_ID=laptop-1\n"
    "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
    "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
)


def test_load_settings_reads_projects_root(tmp_path: Path):
    projects_root = tmp_path / "projects"
    projects_root.mkdir()
    env_file = tmp_path / ".env"
    env_file.write_text(NODE_VALUES + f"VENUS_NODE_PROJECTS_ROOT={projects_root}\n")

    settings = load_settings(env_file)

    assert settings.projects_root == projects_root


def test_load_settings_projects_root_defaults_to_none(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(NODE_VALUES)

    settings = load_settings(env_file)

    assert settings.projects_root is None


def test_load_settings_rejects_missing_projects_root(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(NODE_VALUES + f"VENUS_NODE_PROJECTS_ROOT={tmp_path / 'missing'}\n")

    with pytest.raises(ValueError, match="VENUS_NODE_PROJECTS_ROOT must be an existing folder"):
        load_settings(env_file)


def test_load_settings_wake_defaults_to_vosk_and_venus_phrases(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(NODE_VALUES + "VENUS_NODE_WAKE_MODEL=\n")

    settings = load_settings(env_file)

    assert settings.wake_model == "models/vosk-model-small-en-us-0.15"
    assert settings.wake_phrases == ["hey venus", "venus", "hey love"]


def test_load_settings_reads_wake_model_and_phrases(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        NODE_VALUES
        + "VENUS_NODE_WAKE_MODEL=D:/wake/vosk\n"
        + "VENUS_NODE_WAKE_PHRASES= Hey Venus, babe venus ,,\n"
    )

    settings = load_settings(env_file)

    assert settings.wake_model == "D:/wake/vosk"
    assert settings.wake_phrases == ["hey venus", "babe venus"]
