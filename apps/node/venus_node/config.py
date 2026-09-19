from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class NodeSettings:
    device_id: str
    spotify_target: str
    core_dev_token: str
    core_url: str


def load_settings(env_file: Path) -> NodeSettings:
    values = dotenv_values(env_file)

    device_id = values.get("VENUS_NODE_DEVICE_ID", "")
    spotify_target = values.get("VENUS_NODE_SPOTIFY_TARGET", "")
    core_dev_token = values.get("VENUS_NODE_CORE_DEV_TOKEN", "")
    core_url = values.get("VENUS_NODE_CORE_URL", "")

    if not device_id.strip():
        raise ValueError("VENUS_NODE_DEVICE_ID is required")

    if not spotify_target.strip():
        raise ValueError("VENUS_NODE_SPOTIFY_TARGET is required")

    if not core_dev_token.strip():
        raise ValueError("VENUS_NODE_CORE_DEV_TOKEN is required")

    if not core_url.strip():
        raise ValueError("VENUS_NODE_CORE_URL is required")

    return NodeSettings(
        device_id=device_id,
        spotify_target=spotify_target,
        core_dev_token=core_dev_token,
        core_url=core_url,
    )
