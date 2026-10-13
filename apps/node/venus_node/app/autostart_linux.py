import os
import sys
from pathlib import Path

# KDE, GNOME and most Linux desktops start every .desktop file in this
# folder at login (the XDG autostart standard). No root needed.
NAME = "Venus"
LABEL = "Start at login"


def autostart_dir(environ: dict[str, str] | None = None) -> Path:
    environ = os.environ if environ is None else environ
    return Path(environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "autostart"


DEFAULT_KEY = str(autostart_dir() / "venus.desktop")


def background_python() -> Path:
    # Linux has no pythonw: the same Python, with --hidden so it logs to a file.
    return Path(sys.executable)


def quote(word: str) -> str:
    # Exec quoting from the desktop entry spec: inside "...", escape " ` $ and \.
    for special in ("\\", '"', "`", "$"):
        word = word.replace(special, "\\" + special)
    return f'"{word}"'


def launch_command(python: Path, launcher: Path) -> str:
    return f"{quote(str(python))} {quote(str(launcher))} --hidden"


def desktop_file(command: str) -> str:
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={NAME}\n"
        "Comment=Venus on this PC: Hey Venus, the orb and the tray icon\n"
        f"Exec={command}\n"
        "Terminal=false\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def is_enabled(key: str = DEFAULT_KEY) -> bool:
    path = Path(key)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    # The desktop's own Autostart settings switch an entry off with Hidden=true.
    return "Hidden=true" not in text


def enable(command: str, key: str = DEFAULT_KEY) -> None:
    path = Path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(desktop_file(command), encoding="utf-8")


def approve_missing(key: str = DEFAULT_KEY) -> None:
    """Only Windows needs this (its Task Manager switch); nothing to fix here."""


def disable(key: str = DEFAULT_KEY) -> None:
    Path(key).unlink(missing_ok=True)
