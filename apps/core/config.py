from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class CoreSettings:
    dev_node_token: str

@dataclass(frozen=True)
class NodeSettings:
    device_id: str
    spotify_target: str
    core_dev_token: str

def get_settings() -> CoreSettings:
    core_directory = Path(__file__).resolve().parent
    return load_settings(core_directory / ".env")


def load_settings(env_file: Path) -> CoreSettings:
    values = dotenv_values(env_file)
    token = values.get("VENUS_CORE_DEV_NODE_TOKEN", "")

    if not token.strip():
        raise ValueError("VENUS_CORE_DEV_NODE_TOKEN is required")

    return CoreSettings(dev_node_token=token)
