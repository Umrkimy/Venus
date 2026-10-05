import winreg
from pathlib import Path

# Per-user list of programs Windows starts at login; no admin needed.
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
NAME = "Venus"


def launch_command(pythonw: Path, launcher: Path) -> str:
    # Quoted: the paths may have spaces.
    return f'"{pythonw}" "{launcher}"'


def is_enabled(key: str = RUN_KEY) -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as run:
            winreg.QueryValueEx(run, NAME)
    except FileNotFoundError:
        return False
    return True


def enable(command: str, key: str = RUN_KEY) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as run:
        winreg.SetValueEx(run, NAME, 0, winreg.REG_SZ, command)


def disable(key: str = RUN_KEY) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_SET_VALUE) as run:
            winreg.DeleteValue(run, NAME)
    except FileNotFoundError:
        pass  # Already off.
