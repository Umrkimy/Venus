import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from venus_node.app.autostart import approve_missing, background_python, launch_command
from venus_node.app.domain import start_domain
from venus_node.app.reminders import Reminders, desktop_notifier, fetch_upcoming, start_reminders
from venus_node.app.server import STARTING, Server, runs_here
from venus_node.app.single import (
    CONNECTION,
    LISTENER,
    already_running_message,
    claim,
    quit_signal,
    wait_for_quit,
)
from venus_node.app.tray import Tray
from venus_node.commands.pc import IS_MAC, IS_WINDOWS
from venus_node.cli.dev_connect import run_connect
from venus_node.cli.listen import start_listening, wake_listeners
from venus_node.config import load_settings
from venus_node.voice.status import Status
from venus_protocol.schemas.connections import NodeHello

MB_ICONINFORMATION = 0x40
NODE_DIRECTORY = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = NODE_DIRECTORY.parent.parent


def log_to_file(path: Path) -> None:
    # pythonw has no console, so print() and crash messages would vanish.
    path.parent.mkdir(parents=True, exist_ok=True)
    # "w": only the last run, so the file never grows forever.
    log = open(path, "w", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = log
    print(f"Venus started {datetime.now():%Y-%m-%d %H:%M:%S}")


def show_message(text: str) -> None:
    # Started hidden there's no console to print to, so a small popup instead.
    if IS_WINDOWS:
        import ctypes

        ctypes.WinDLL("user32").MessageBoxW(None, text, "Venus", MB_ICONINFORMATION)
        return
    if IS_MAC:
        from venus_node.commands.mac_apps import notify_mac

        notify_mac("Venus", text)
        return
    notify_send = shutil.which("notify-send")
    if notify_send:
        subprocess.run([notify_send, "Venus", text], check=False, timeout=10)
    else:
        print(text, file=sys.stderr)


def run_app(node_directory: Path) -> None:
    """Connection, listener, orb and tray icon in one process."""
    env_file = node_directory / ".env"
    settings = load_settings(env_file)
    status = Status()
    muted = threading.Event()

    def quit() -> None:
        print("Quitting.")
        status.close()  # The orb window closes on its next tick.

    # A restart from a script quits like the tray's Quit, so the icon is removed.
    # Killing the process instead leaves a dead icon by the clock until you hover it.
    signal = quit_signal()
    threading.Thread(target=lambda: (wait_for_quit(signal), quit()), daemon=True).start()

    # The main PC starts the Venus server itself, so the Venus icon is all you click.
    server = None
    if settings.start_server and runs_here(settings.core_url, REPO_ROOT, shutil.which):
        server = Server(REPO_ROOT, settings.core_url, on_change=lambda: tray.refresh())

    def restart() -> None:
        if server.state != STARTING:
            threading.Thread(target=server.restart, daemon=True).start()

    tray = Tray(
        muted,
        open_venus=lambda: webbrowser.open(settings.web_url),
        autostart_command=launch_command(background_python(), node_directory / "venus.pyw"),
        quit=quit,
        stop_talking=status.request_stop,
        server=(lambda: (server.state, server.detail)) if server else None,
        restart=restart if server else None,
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

    # Your own domain, only if VENUS_DOMAIN is set in the root .env.
    domain = start_domain(REPO_ROOT, node_directory / "data" / "caddy.log")

    # A pop-up ~10 minutes before calendar events (when a calendar is connected).
    reminders_stop = threading.Event()
    start_reminders(
        Reminders(
            fetch=lambda: fetch_upcoming(settings),
            notify=desktop_notifier(lambda text, title: tray.icon.notify(text, title)),
            clock=lambda: datetime.now().astimezone(),
        ),
        reminders_stop,
    )

    # setup runs once the icon is up: a toast, or a new icon is easy to miss under "^".
    tray.icon.run_detached(setup=announce)
    if server is not None:

        def start_server() -> None:
            if server.start():
                tray.icon.notify("Venus is ready.", "Venus")

        threading.Thread(target=start_server, daemon=True).start()
    try:
        from venus_node.voice.window import orb_window

        Circle = orb_window()

        # The orb window owns the main thread until Quit (or a mic error).
        Circle(status).run()
    finally:
        reminders_stop.set()
        if domain is not None:
            domain.stop()
        tray.icon.stop()


def announce(icon) -> None:
    icon.visible = True
    print("Tray icon shown.")
    try:
        icon.notify("Venus is running. Right-click the dot by the clock for the menu.", "Venus")
    except NotImplementedError:
        pass  # Some Linux tray backends can't show toasts; the icon is enough.


def open_running_venus() -> bool:
    try:
        settings = load_settings(NODE_DIRECTORY / ".env")
    except ValueError:
        return False
    return webbrowser.open(settings.web_url)


def main() -> None:
    # pythonw (Windows) has no stdout; Linux autostart and start-venus.sh pass --hidden.
    hidden = sys.stdout is None or "--hidden" in sys.argv
    # Claim first: a second start must not wipe the running app's log.
    if not claim(CONNECTION) or not claim(LISTENER):
        # Clicking the Venus icon again opens Venus instead of a popup.
        if hidden and open_running_venus():
            return
        message = already_running_message("Venus") + " Look for the dot by the clock."
        if hidden:
            show_message(message)
        else:
            print(message)
        return
    if hidden:
        log_to_file(NODE_DIRECTORY / "data" / "venus-node.log")
    approve_missing()  # "Start with Windows" ticked before S28 never ran at login.
    run_app(NODE_DIRECTORY)
