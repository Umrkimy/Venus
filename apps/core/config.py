import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

# Free Fish Audio model to start with; VENUS_CORE_FISH_MODEL=s2.1-pro is the paid one.
FISH_MODEL = "s2.1-pro-free"


@dataclass(frozen=True)
class CoreSettings:
    dev_node_token: str
    # Empty = off. Only for curl testing; the web page logs in with cookies.
    dev_owner_token: str
    database_url: str
    llm_provider: str = "fake"
    llm_model: str = ""
    llm_api_key: str = ""
    secret_key: str = ""
    fish_api_key: str = ""
    fish_voice_id: str = ""
    fish_model: str = FISH_MODEL


def get_settings() -> CoreSettings:
    core_directory = Path(__file__).resolve().parent
    return load_settings(core_directory / ".env")


def load_settings(env_file: Path) -> CoreSettings:
    values = dotenv_values(env_file)
    # Real environment variables win over the file. Docker passes settings
    # this way, for example the database address inside the compose network.
    values.update(
        (name, value)
        for name, value in os.environ.items()
        if name.startswith("VENUS_CORE_")
    )
    node_token = values.get("VENUS_CORE_DEV_NODE_TOKEN", "")
    owner_token = (values.get("VENUS_CORE_DEV_OWNER_TOKEN") or "").strip()
    database_url = values.get("VENUS_CORE_DATABASE_URL", "")
    llm_provider = values.get("VENUS_CORE_LLM_PROVIDER") or "fake"
    llm_model = values.get("VENUS_CORE_LLM_MODEL") or ""
    llm_api_key = values.get("VENUS_CORE_LLM_API_KEY") or ""
    secret_key = values.get("VENUS_CORE_SECRET_KEY") or ""
    fish_api_key = values.get("VENUS_CORE_FISH_API_KEY") or ""
    fish_voice_id = values.get("VENUS_CORE_FISH_VOICE_ID") or ""
    fish_model = values.get("VENUS_CORE_FISH_MODEL") or FISH_MODEL

    if not node_token or not node_token.strip():
        raise ValueError("VENUS_CORE_DEV_NODE_TOKEN is required")

    if not database_url or not database_url.strip():
        raise ValueError("VENUS_CORE_DATABASE_URL is required")

    return CoreSettings(
        dev_node_token=node_token,
        dev_owner_token=owner_token,
        database_url=database_url,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        secret_key=secret_key,
        fish_api_key=fish_api_key,
        fish_voice_id=fish_voice_id,
        fish_model=fish_model,
    )
