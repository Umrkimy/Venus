import ctypes
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183
# "Local\" = only this Windows login session.
CONNECTION = "Local\\VenusNodeConnection"
LISTENER = "Local\\VenusNodeListener"
# Set by `python -m venus_node.app.quit`: the tray app quits cleanly.
QUIT = "Local\\VenusNodeQuit"

EVENT_MODIFY_STATE = 0x0002
INFINITE = 0xFFFFFFFF

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


def _kernel32():
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateEventW.restype = wintypes.HANDLE
    kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.OpenEventW.restype = wintypes.HANDLE
    kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.SetEvent.argtypes = [wintypes.HANDLE]
    kernel32.ResetEvent.argtypes = [wintypes.HANDLE]
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    return kernel32


def quit_signal(name: str = QUIT) -> int:
    """A named Windows event another process can set to ask this one to quit."""
    kernel32 = _kernel32()
    handle = kernel32.CreateEventW(None, True, False, name)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    # A quit meant for the app before us may still be set: start clear.
    kernel32.ResetEvent(handle)
    _held.append(handle)
    return handle


def wait_for_quit(handle: int) -> None:
    """Blocks until someone asks this app to quit."""
    _kernel32().WaitForSingleObject(handle, INFINITE)


def ask_to_quit(name: str = QUIT) -> bool:
    """Ask the running tray app to quit; False if none is running."""
    kernel32 = _kernel32()
    handle = kernel32.OpenEventW(EVENT_MODIFY_STATE, False, name)
    if not handle:
        return False
    kernel32.SetEvent(handle)
    kernel32.CloseHandle(handle)
    return True


def already_running_message(part: str) -> str:
    return f"{part} is already running (Venus tray app or another window). Quit it first."
