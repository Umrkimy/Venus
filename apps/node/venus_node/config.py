from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class NodeSettings:
    device_id: str
    core_dev_token: str
    core_url: str
    real_actions: bool = False
    projects_root: Path | None = None


def load_settings(env_file: Path) -> NodeSettings:
    values = dotenv_values(env_file)

    device_id = values.get("VENUS_NODE_DEVICE_ID", "")
    core_dev_token = values.get("VENUS_NODE_CORE_DEV_TOKEN", "")
    core_url = values.get("VENUS_NODE_CORE_URL", "")
    raw_real_actions = (values.get("VENUS_NODE_REAL_ACTIONS") or "false").strip().lower()
    raw_projects_root = (values.get("VENUS_NODE_PROJECTS_ROOT") or "").strip()
    projects_root = Path(raw_projects_root) if raw_projects_root else None

    if not device_id.strip():
        raise ValueError("VENUS_NODE_DEVICE_ID is required")

    if not core_dev_token.strip():
        raise ValueError("VENUS_NODE_CORE_DEV_TOKEN is required")

    if not core_url.strip():
        raise ValueError("VENUS_NODE_CORE_URL is required")

    if raw_real_actions not in ("true", "false"):
        raise ValueError("VENUS_NODE_REAL_ACTIONS must be true or false")

    real_actions = raw_real_actions == "true"

    if projects_root is not None and not projects_root.is_dir():
        raise ValueError("VENUS_NODE_PROJECTS_ROOT must be an existing folder")

    return NodeSettings(
        device_id=device_id,
        core_dev_token=core_dev_token,
        core_url=core_url,
        real_actions=real_actions,
        projects_root=projects_root,
    )
