from collections.abc import Callable
from threading import Event, Lock

import pystray
from PIL import Image, ImageDraw

from venus_node.app import autostart

CRIMSON = (225, 29, 72, 255)  # Tailwind rose-600, the web theme's crimson (D-44).
GREY = (128, 128, 128, 255)


def icon_image(color: tuple[int, int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((8, 8, 56, 56), fill=color)
    return image


def status_text(connected: bool, muted: bool) -> str:
    text = "Connected" if connected else "Core offline"
    return f"{text}, mic muted" if muted else text


class Tray:
    """The icon by the clock and its right-click menu.

    The connection thread, the tray thread and Quit all touch it,
    so `connected` goes through a lock and `muted` is an Event.
    """

    def __init__(
        self,
        muted: Event,
        open_venus: Callable[[], None],
        autostart_command: str,
        quit: Callable[[], None],
        autostart_key: str = autostart.RUN_KEY,
        stop_talking: Callable[[], None] = lambda: None,
    ) -> None:
        self._lock = Lock()
        self._connected = False
        self.muted = muted
        self._open_venus = open_venus
        self.autostart_command = autostart_command
        self._quit = quit
        self._stop_talking = stop_talking
        self.autostart_key = autostart_key
        self.icon = pystray.Icon("Venus", icon_image(GREY), "Venus", self.menu())

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._connected

    def set_connected(self, connected: bool) -> None:
        with self._lock:
            self._connected = connected
        self.refresh()

    def menu(self) -> pystray.Menu:
        return pystray.Menu(
            # Grey line at the top: is Venus alive?
            pystray.MenuItem(lambda item: status_text(self.connected, self.muted.is_set()), None, enabled=False),
            pystray.Menu.SEPARATOR,
            # default=True: a left click on the icon does this too.
            pystray.MenuItem("Open Venus", self.open_venus, default=True),
            pystray.MenuItem("Stop talking", self.stop_talking),
            pystray.MenuItem("Mute mic", self.toggle_mute, checked=lambda item: self.muted.is_set()),
            pystray.MenuItem(
                "Start with Windows",
                self.toggle_autostart,
                checked=lambda item: autostart.is_enabled(self.autostart_key),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit),
        )

    def refresh(self) -> None:
        # Crimson only when Venus can actually hear you and answer.
        live = self.connected and not self.muted.is_set()
        self.icon.icon = icon_image(CRIMSON if live else GREY)
        self.icon.title = f"Venus: {status_text(self.connected, self.muted.is_set())}"
        # pystray builds the menu text once; rebuild it so the status line is current.
        self.icon.update_menu()

    def open_venus(self) -> None:
        self._open_venus()

    def stop_talking(self) -> None:
        # Luna stops mid-sentence, or drops an answer that hasn't started.
        self._stop_talking()

    def toggle_mute(self) -> None:
        self.set_muted(not self.muted.is_set())

    def set_muted(self, muted: bool) -> None:
        """Mute or unmute; the web's orb button arrives here too."""
        if muted:
            self.mute()
        elif self.muted.is_set():
            self.muted.clear()
            print("Mic on.")
            self.refresh()

    def mute(self) -> None:
        # Also called from the mic thread when you say "mute the mic".
        self.muted.set()
        print("Mic muted.")
        self.refresh()

    def toggle_autostart(self) -> None:
        if autostart.is_enabled(self.autostart_key):
            autostart.disable(self.autostart_key)
            print("Venus won't start with Windows.")
        else:
            autostart.enable(self.autostart_command, self.autostart_key)
            print("Venus will start with Windows.")
        self.refresh()

    def quit(self) -> None:
        self._quit()
