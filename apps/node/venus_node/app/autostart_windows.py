import sys
import winreg
from pathlib import Path

# Per-user list of programs Windows starts at login; no admin needed.
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
# Task Manager's on/off switch for each Run entry. New Windows 11 skips a Run
# entry with no switch here, so Venus never started at login (found S28).
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
NAME = "Venus"
DEFAULT_KEY = RUN_KEY
# The tray menu line.
LABEL = "Start with Windows"
# First byte 2 = enabled (what Task Manager writes); odd (3) = disabled by the user.
ENABLED = bytes([2] + [0] * 11)


def background_python() -> Path:
    # pythonw has no console window.
    return Path(sys.executable).with_name("pythonw.exe")


def launch_command(pythonw: Path, launcher: Path) -> str:
    # Quoted: the paths may have spaces.
    return f'"{pythonw}" "{launcher}"'


def approved_key(key: str) -> str:
    # Tests pass a throwaway Run key; their switch lives under it, never in the real list.
    return APPROVED_KEY if key == RUN_KEY else key + r"\Approved"


def read(key: str):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as values:
            return winreg.QueryValueEx(values, NAME)[0]
    except FileNotFoundError:
        return None


def switch_on(key: str) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, approved_key(key)) as approved:
        winreg.SetValueEx(approved, NAME, 0, winreg.REG_BINARY, ENABLED)


def is_enabled(key: str = RUN_KEY) -> bool:
    # On only if Windows will really start it: command there and switch on.
    switch = read(approved_key(key))
    return read(key) is not None and switch is not None and switch[0] % 2 == 0


def enable(command: str, key: str = RUN_KEY) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as run:
        winreg.SetValueEx(run, NAME, 0, winreg.REG_SZ, command)
    switch_on(key)


def approve_missing(key: str = RUN_KEY) -> None:
    """Fix entries saved before S28: add the switch, but never undo a user's Disable."""
    if read(key) is not None and read(approved_key(key)) is None:
        switch_on(key)


def disable(key: str = RUN_KEY) -> None:
    for each in (key, approved_key(key)):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, each, 0, winreg.KEY_SET_VALUE) as values:
                winreg.DeleteValue(values, NAME)
        except FileNotFoundError:
            pass  # Already off.
