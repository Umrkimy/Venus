import os
import shlex
import shutil
import subprocess
from collections.abc import Callable
from configparser import ConfigParser, Error as ConfigError
from pathlib import Path

from venus_node.commands.start_apps import StartApp

# Linux's Start menu: every app menu (KDE, GNOME, ...) is built from these
# .desktop files. The file name ("firefox.desktop") is the app's id.
FLATPAK_DIRS = (
    Path("/var/lib/flatpak/exports/share"),
    Path.home() / ".local/share/flatpak/exports/share",
)
# %f, %u and friends are where a launcher puts files; Venus opens apps without any.
FIELD_CODES = {"%f", "%F", "%u", "%U", "%d", "%D", "%n", "%N", "%i", "%c", "%k", "%v", "%m"}


def application_dirs(environ: dict[str, str] | None = None) -> list[Path]:
    """Where .desktop files live, most important first (yours beat the system's)."""
    environ = os.environ if environ is None else environ
    data_home = Path(environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    data_dirs = (environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share").split(":")
    roots = [data_home, *(Path(d) for d in data_dirs if d), *FLATPAK_DIRS]
    seen: list[Path] = []
    for root in roots:
        folder = root / "applications"
        if folder not in seen:
            seen.append(folder)
    return seen


def desktop_entry(text: str) -> dict[str, str] | None:
    """The [Desktop Entry] keys of one .desktop file, or None if it can't be read."""
    parser = ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str  # Keys are case-sensitive: Name, not name.
    try:
        parser.read_string(text)
    except ConfigError:
        return None
    if not parser.has_section("Desktop Entry"):
        return None
    return dict(parser["Desktop Entry"])


def shown_app(entry: dict[str, str]) -> bool:
    """Apps a menu would show: real apps, not hidden helpers or broken entries."""
    return (
        entry.get("Type") == "Application"
        and bool(entry.get("Name"))
        and bool(entry.get("Exec"))
        and entry.get("NoDisplay", "").lower() != "true"
        and entry.get("Hidden", "").lower() != "true"
    )


def desktop_files(dirs: list[Path]) -> dict[str, Path]:
    """Every app id and its file. The first folder with an id wins, like the menus."""
    found: dict[str, Path] = {}
    for folder in dirs:
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*.desktop")):
            # Files in subfolders get the folder in their id: kde4/okular.desktop -> kde4-okular.desktop.
            app_id = path.relative_to(folder).as_posix().replace("/", "-")
            found.setdefault(app_id, path)
    return found


def read_entry(path: Path) -> dict[str, str] | None:
    try:
        return desktop_entry(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None


def read_desktop_apps(dirs: list[Path]) -> list[StartApp]:
    apps = []
    for app_id, path in desktop_files(dirs).items():
        entry = read_entry(path)
        # A file in your own folder with Hidden=true hides the system one too: it isn't listed.
        if entry is not None and shown_app(entry):
            apps.append(StartApp(name=entry["Name"], app_id=app_id))
    return sorted(apps, key=lambda app: app.name.lower())


def exec_command(exec_line: str) -> list[str]:
    """The Exec line as a program and its arguments, without the file placeholders."""
    words = shlex.split(exec_line)
    return [word.replace("%%", "%") for word in words if word not in FIELD_CODES]


def launch_desktop_app(
    app_id: str,
    dirs: list[Path] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    popen=subprocess.Popen,
) -> None:
    """Start the app like clicking it in the menu.

    gio (part of GLib, on KDE and GNOME alike) handles Terminal=true and
    D-Bus apps. Without it, run the Exec line ourselves: a list, never a
    shell, so nothing in the file can chain other commands.
    """
    path = desktop_files(dirs if dirs is not None else application_dirs()).get(app_id)
    entry = read_entry(path) if path is not None else None
    if path is None or entry is None or not shown_app(entry):
        raise FileNotFoundError(f"No app {app_id}")
    gio = which("gio")
    command = [gio, "launch", str(path)] if gio else exec_command(entry["Exec"])
    # Own session: closing Venus never closes the app it opened.
    popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
