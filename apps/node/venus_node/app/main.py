import ctypes
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from venus_node.app.autostart import launch_command
from venus_node.app.single import CONNECTION, LISTENER, already_running_message, claim
from venus_node.app.tray import Tray
from venus_node.cli.dev_connect import run_connect
from venus_node.cli.listen import start_listening, wake_listeners
from venus_node.config import load_settings
from venus_node.voice.status import Status
from venus_protocol.schemas.connections import NodeHello

MB_ICONINFORMATION = 0x40
NODE_DIRECTORY = Path(__file__).resolve().parent.parent.parent


def log_to_file(path: Path) -> None:
    # pythonw has no console, so print() and crash messages would vanish.
    path.parent.mkdir(parents=True, exist_ok=True)
    # "w": only the last run, so the file never grows forever.
    log = open(path, "w", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = log
    print(f"Venus started {datetime.now():%Y-%m-%d %H:%M:%S}")


def show_message(text: str) -> None:
    # pythonw has no console to print to, so a small Windows popup instead.
    ctypes.WinDLL("user32").MessageBoxW(None, text, "Venus", MB_ICONINFORMATION)


def run_app(node_directory: Path) -> None:
    """Connection, listener, orb and tray icon in one process."""
    env_file = node_directory / ".env"
    settings = load_settings(env_file)
    status = Status()
    muted = threading.Event()

    def quit() -> None:
        print("Quitting.")
        status.close()  # The orb window closes on its next tick.

    tray = Tray(
        muted,
        open_venus=lambda: webbrowser.open(settings.web_url),
        autostart_command=launch_command(
            Path(sys.executable).with_name("pythonw.exe"),
            node_directory / "venus.pyw",
        ),
        quit=quit,
    )

    def connected(hello: NodeHello) -> None:
        print(f"Core confirmed Node: {hello.device_id}")
        tray.set_connected(True)

    def retry() -> None:
        # Printed once per drop, not every second while Core is down.
        if tray.connected:
            print("Lost Core; retrying every second")
        tray.set_connected(False)

    threading.Thread(target=run_connect, args=(env_file, connected, retry), daemon=True).start()

    listeners = wake_listeners(env_file, settings)
    if listeners is not None:
        start_listening(settings, *listeners, status, muted, tray.mute)

    # setup runs once the icon is up: a toast, or a new icon is easy to miss under "^".
    tray.icon.run_detached(setup=announce)
    try:
        # Imported here: the orb window needs a real desktop.
        from venus_node.voice.circle import Circle

        # The orb window owns the main thread until Quit (or a mic error).
        Circle(status).run()
    finally:
        tray.icon.stop()


def announce(icon) -> None:
    icon.visible = True
    print("Tray icon shown.")
    icon.notify("Venus is running. Right-click the dot by the clock for the menu.", "Venus")


def main() -> None:
    hidden = sys.stdout is None  # Started with pythonw.
    # Claim first: a second start must not wipe the running app's log.
    if not claim(CONNECTION) or not claim(LISTENER):
        message = already_running_message("Venus") + " Look for the dot by the clock."
        if hidden:
            show_message(message)
        else:
            print(message)
        return
    if hidden:
        log_to_file(NODE_DIRECTORY / "data" / "venus-node.log")
    run_app(NODE_DIRECTORY)
