from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

WAKE_PHRASES = ("hey venus", "venus")
WEB_URL = "http://localhost:3000"


@dataclass(frozen=True)
class NodeSettings:
    device_id: str
    core_dev_token: str
    core_url: str
    real_actions: bool = False
    projects_root: Path | None = None
    wake_model: str = "models/vosk-model-small-en-us-0.15"
    wake_phrases: list[str] = field(default_factory=lambda: list(WAKE_PHRASES))
    web_url: str = WEB_URL
    mic: str = ""
    # False on extra PCs: no "Hey Venus" (and no speech model in RAM).
    voice: bool = True
    # The tray starts Docker and the Venus server when they're on this PC.
    start_server: bool = True
    # Venus says calendar reminders out loud (with voice on), not just a pop-up.
    speak_reminders: bool = True


def load_settings(env_file: Path) -> NodeSettings:
    values = dotenv_values(env_file)

    device_id = values.get("VENUS_NODE_DEVICE_ID", "")
    core_dev_token = values.get("VENUS_NODE_CORE_DEV_TOKEN", "")
    core_url = values.get("VENUS_NODE_CORE_URL", "")
    raw_real_actions = (values.get("VENUS_NODE_REAL_ACTIONS") or "false").strip().lower()
    raw_projects_root = (values.get("VENUS_NODE_PROJECTS_ROOT") or "").strip()
    projects_root = Path(raw_projects_root) if raw_projects_root else None
    wake_model = (values.get("VENUS_NODE_WAKE_MODEL") or "").strip() or "models/vosk-model-small-en-us-0.15"
    # "hey venus, venus" -> ["hey venus", "venus"]; Vosk wants lowercase words.
    raw_phrases = (values.get("VENUS_NODE_WAKE_PHRASES") or "").lower()
    wake_phrases = [p.strip() for p in raw_phrases.split(",") if p.strip()] or list(WAKE_PHRASES)
    # Where the tray's "Open Venus" goes.
    web_url = (values.get("VENUS_NODE_WEB_URL") or "").strip() or WEB_URL
    # Part of the mic's name, e.g. "Realtek"; empty = the default mic.
    mic = (values.get("VENUS_NODE_MIC") or "").strip()
    raw_voice = (values.get("VENUS_NODE_VOICE") or "true").strip().lower()
    raw_start_server = (values.get("VENUS_NODE_START_SERVER") or "true").strip().lower()
    raw_speak_reminders = (values.get("VENUS_NODE_SPEAK_REMINDERS") or "true").strip().lower()

    if not device_id.strip():
        raise ValueError("VENUS_NODE_DEVICE_ID is required")

    if not core_dev_token.strip():
        raise ValueError("VENUS_NODE_CORE_DEV_TOKEN is required")

    if not core_url.strip():
        raise ValueError("VENUS_NODE_CORE_URL is required")

    if raw_real_actions not in ("true", "false"):
        raise ValueError("VENUS_NODE_REAL_ACTIONS must be true or false")

    real_actions = raw_real_actions == "true"

    if raw_voice not in ("true", "false"):
        raise ValueError("VENUS_NODE_VOICE must be true or false")

    if raw_start_server not in ("true", "false"):
        raise ValueError("VENUS_NODE_START_SERVER must be true or false")

    if raw_speak_reminders not in ("true", "false"):
        raise ValueError("VENUS_NODE_SPEAK_REMINDERS must be true or false")

    if projects_root is not None and not projects_root.is_dir():
        raise ValueError("VENUS_NODE_PROJECTS_ROOT must be an existing folder")

    return NodeSettings(
        device_id=device_id,
        core_dev_token=core_dev_token,
        core_url=core_url,
        real_actions=real_actions,
        projects_root=projects_root,
        wake_model=wake_model,
        wake_phrases=wake_phrases,
        web_url=web_url,
        mic=mic,
        voice=raw_voice == "true",
        start_server=raw_start_server == "true",
        speak_reminders=raw_speak_reminders == "true",
    )
