from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class NodeSettings:
    device_id: str
    spotify_target: str


def load_settings(env_file: Path) -> NodeSettings:
    values = dotenv_values(env_file)

    device_id = values.get("VENUS_NODE_DEVICE_ID", "")
    spotify_target = values.get("VENUS_NODE_SPOTIFY_TARGET", "")

    if not device_id.strip():
        raise ValueError("VENUS_NODE_DEVICE_ID is required")

    if not spotify_target.strip():
        raise ValueError("VENUS_NODE_SPOTIFY_TARGET is required")

    return NodeSettings(
        device_id=device_id,
        spotify_target=spotify_target,
    )