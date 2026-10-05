import ctypes
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183
# "Local\" = only this Windows login session.
CONNECTION = "Local\\VenusNodeConnection"
LISTENER = "Local\\VenusNodeListener"

# Kept open on purpose: Windows frees the names when this process exits.
_held: list[int] = []


def claim(name: str) -> bool:
    """True if no other Venus process already holds this name.

    Stops autostart plus a manual start from running two listeners
    (two answers per "Hey Venus") or two connections.
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return False
    _held.append(handle)
    return True


def already_running_message(part: str) -> str:
    return f"{part} is already running (Venus tray app or another window). Quit it first."
