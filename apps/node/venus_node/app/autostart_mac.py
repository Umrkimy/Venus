import plistlib
import shlex
import sys
from pathlib import Path

# macOS starts every LaunchAgent in this folder when you log in. No admin needed.
NAME = "dev.venus.node"
LABEL = "Start at login"
DEFAULT_KEY = str(Path.home() / "Library" / "LaunchAgents" / f"{NAME}.plist")


def background_python() -> Path:
    # Like Linux: the same Python, with --hidden so it logs to a file.
    return Path(sys.executable)


def launch_command(python: Path, launcher: Path) -> str:
    return f"{shlex.quote(str(python))} {shlex.quote(str(launcher))} --hidden"


def agent(command: str) -> bytes:
    """The LaunchAgent: run Venus once at login, as a list of words (no shell)."""
    return plistlib.dumps({
        "Label": NAME,
        "ProgramArguments": shlex.split(command),
        "RunAtLoad": True,
        "ProcessType": "Interactive",
    })


def is_enabled(key: str = DEFAULT_KEY) -> bool:
    return Path(key).is_file()


def enable(command: str, key: str = DEFAULT_KEY) -> None:
    path = Path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(agent(command))


def approve_missing(key: str = DEFAULT_KEY) -> None:
    """Only Windows needs this (its Task Manager switch); nothing to fix here."""


def disable(key: str = DEFAULT_KEY) -> None:
    Path(key).unlink(missing_ok=True)
