"""The Mac's apps: every .app bundle in the Applications folders, like Launchpad.

An app's id is its bundle path ("/Applications/Spotify.app"), and opening it
is `open -a <path>`, the same as double-clicking it in Finder.
"""

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from venus_node.commands.start_apps import StartApp


def application_dirs(home: Path | None = None) -> list[Path]:
    """Where apps live, yours first (Launchpad shows these)."""
    home = home or Path.home()
    return [
        home / "Applications",
        Path("/Applications"),
        Path("/Applications/Utilities"),
        Path("/System/Applications"),
        Path("/System/Applications/Utilities"),
    ]


def app_bundles(dirs: list[Path]) -> dict[str, Path]:
    """App name -> bundle path; a name found first wins (your own copy beats the system's)."""
    found: dict[str, Path] = {}
    for folder in dirs:
        try:
            bundles = sorted(folder.glob("*.app"))
        except OSError:
            continue
        for bundle in bundles:
            found.setdefault(bundle.stem, bundle)
    return found


def read_mac_apps(dirs: list[Path]) -> list[StartApp]:
    apps = [StartApp(name=name, app_id=str(path)) for name, path in app_bundles(dirs).items()]
    return sorted(apps, key=lambda app: app.name.lower())


def launch_mac_app(
    app_id: str,
    dirs: list[Path] | None = None,
    popen=subprocess.Popen,
) -> None:
    """Open an app from the list, never any other path."""
    known = {str(path) for path in app_bundles(dirs if dirs is not None else application_dirs()).values()}
    if app_id not in known:
        raise FileNotFoundError(f"No app {app_id}")
    # A list, not a shell; its own session so quitting Venus never closes the app.
    popen(
        ["open", "-a", app_id],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def open_with_mac(target: str, popen=subprocess.Popen) -> None:
    """A link in the default browser (`open` picks the right app)."""
    popen(
        ["open", target],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def open_folder_in_code(
    folder: Path,
    which: Callable[[str], str | None] = shutil.which,
    popen=subprocess.Popen,
) -> None:
    """VS Code's `code` command if it's installed, else the app itself."""
    cli = which("code")
    command = [cli, str(folder)] if cli else ["open", "-a", "Visual Studio Code", str(folder)]
    popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def notify_mac(title: str, text: str, run=subprocess.run) -> None:
    """A Notification Center banner. The text goes in as a script argument, never as code."""
    script = "on run argv\ndisplay notification (item 2 of argv) with title (item 1 of argv)\nend run"
    run(["osascript", "-e", script, title, text], check=False, timeout=10, capture_output=True)
