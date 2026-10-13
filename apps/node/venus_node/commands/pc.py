import shutil
import subprocess
import sys
from pathlib import Path

from venus_node.commands.start_apps import StartApp

# The only place that asks which OS this is: Windows, Mac, or Linux (CachyOS and others).
IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

# Linux editors that understand `<cli> <folder>`, in the order tried.
LINUX_CODE_COMMANDS = ("code", "code-oss", "codium")


def list_apps() -> list[StartApp]:
    """Apps this PC can open: the Start menu on Windows, Applications on a Mac, .desktop files on Linux."""
    if IS_WINDOWS:
        from venus_node.commands.start_apps import read_start_apps, run_powershell

        return read_start_apps(run_powershell)
    if IS_MAC:
        from venus_node.commands.mac_apps import application_dirs, read_mac_apps

        return read_mac_apps(application_dirs())
    from venus_node.commands.desktop_apps import application_dirs, read_desktop_apps

    return read_desktop_apps(application_dirs())


def launch_app(app_id: str) -> None:
    if IS_WINDOWS:
        from venus_node.commands.launcher import start_windows_target

        start_windows_target(f"shell:AppsFolder\\{app_id}")
        return
    if IS_MAC:
        from venus_node.commands.mac_apps import launch_mac_app

        launch_mac_app(app_id)
        return
    from venus_node.commands.desktop_apps import launch_desktop_app

    launch_desktop_app(app_id)


def open_link(url: str) -> None:
    """The default browser opens an http(s) link."""
    if IS_WINDOWS:
        from venus_node.commands.launcher import start_windows_target

        start_windows_target(url)
        return
    if IS_MAC:
        from venus_node.commands.mac_apps import open_with_mac

        open_with_mac(url)
        return
    xdg_open = shutil.which("xdg-open")
    if xdg_open is None:
        raise FileNotFoundError("xdg-open not found")
    subprocess.Popen(
        [xdg_open, url],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def open_folder(folder: Path) -> None:
    """A project folder in VS Code."""
    if IS_WINDOWS:
        from venus_node.commands.launcher import open_in_vscode

        open_in_vscode(folder)
        return
    if IS_MAC:
        from venus_node.commands.mac_apps import open_folder_in_code

        open_folder_in_code(folder)
        return
    cli = next((found for name in LINUX_CODE_COMMANDS if (found := shutil.which(name))), None)
    if cli is None:
        raise FileNotFoundError("VS Code not found")
    # A list, not a shell: the folder name is passed as one argument.
    subprocess.Popen(
        [cli, str(folder)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
