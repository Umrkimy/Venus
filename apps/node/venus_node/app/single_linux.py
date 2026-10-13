import fcntl
import os
import socket
import tempfile
from pathlib import Path

# Same names as on Windows; "Local\" is dropped, files can't have "\".
CONNECTION = "Local\\VenusNodeConnection"
LISTENER = "Local\\VenusNodeListener"
# Set by `python -m venus_node.app.quit`: the tray app quits cleanly.
QUIT = "Local\\VenusNodeQuit"

# Kept open on purpose: Linux drops the lock when this process exits, even on a crash.
_held: list = []


def runtime_dir() -> Path:
    """Per-user folder for locks: /run/user/<id> on systemd PCs, else a private temp folder."""
    base = os.environ.get("XDG_RUNTIME_DIR")
    if base and Path(base).is_dir():
        return Path(base)
    folder = Path(tempfile.gettempdir()) / f"venus-{os.getuid()}"
    folder.mkdir(mode=0o700, exist_ok=True)
    return folder


def file_for(name: str, suffix: str) -> Path:
    return runtime_dir() / (name.split("\\")[-1] + suffix)


def claim(name: str) -> bool:
    """True if no other Venus process already holds this name.

    Stops autostart plus a manual start from running two listeners
    (two answers per "Hey Venus") or two connections.
    """
    handle = open(file_for(name, ".lock"), "a")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return False
    _held.append(handle)
    return True


def quit_signal(name: str = QUIT) -> socket.socket:
    """A socket another process can connect to, to ask this one to quit."""
    path = file_for(name, ".sock")
    # Left over from a crash; claim() already made sure no other Venus runs.
    path.unlink(missing_ok=True)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(path))
    os.chmod(path, 0o600)  # Only you can ask your Venus to quit.
    server.listen(1)
    _held.append(server)
    return server


def wait_for_quit(server: socket.socket) -> None:
    """Blocks until someone asks this app to quit."""
    connection, _ = server.accept()
    connection.close()


def ask_to_quit(name: str = QUIT) -> bool:
    """Ask the running tray app to quit; False if none is running."""
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(str(file_for(name, ".sock")))
    except OSError:
        return False
    finally:
        client.close()
    return True


def already_running_message(part: str) -> str:
    return f"{part} is already running (Venus tray app or another window). Quit it first."
