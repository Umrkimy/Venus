from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class CoreSettings:
    dev_node_token: str
    dev_owner_token: str

def get_settings() -> CoreSettings:
    core_directory = Path(__file__).resolve().parent
    return load_settings(core_directory / ".env")


def load_settings(env_file: Path) -> CoreSettings:
    values = dotenv_values(env_file)
    node_token = values.get("VENUS_CORE_DEV_NODE_TOKEN", "")
    owner_token = values.get("VENUS_CORE_DEV_OWNER_TOKEN", "")

    if not node_token or not node_token.strip():
        raise ValueError("VENUS_CORE_DEV_NODE_TOKEN is required")

    if not owner_token or not owner_token.strip():
        raise ValueError("VENUS_CORE_DEV_OWNER_TOKEN is required")

    return CoreSettings(
        dev_node_token=node_token,
        dev_owner_token=owner_token,
    )
