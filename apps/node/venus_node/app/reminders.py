"""Calendar reminders: a pop-up on the PC about 10 minutes before each event.

Core knows the calendar; the tray app asks it once a minute what starts
soon and shows each event once. Nothing runs when no calendar is connected
(Core just answers an empty list).
"""

import json
import shutil
import subprocess
import threading
from collections.abc import Callable
from datetime import datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from venus_node.commands.pc import IS_MAC, IS_WINDOWS
from venus_node.config import NodeSettings
from venus_node.voice.core_client import core_http_url

CHECK_SECONDS = 60
AHEAD_MINUTES = 10


def fetch_upcoming(settings: NodeSettings) -> list[dict]:
    request = Request(
        f"{core_http_url(settings.core_url)}/calendar/upcoming?minutes={AHEAD_MINUTES}",
        headers={"Authorization": f"Bearer {settings.core_dev_token}"},
    )
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read())


def reminder_text(event: dict, now: datetime) -> str:
    start = datetime.fromisoformat(event["start"])
    minutes = max(0, round((start - now.astimezone(start.tzinfo)).total_seconds() / 60))
    when = "now" if minutes == 0 else f"in {minutes} min"
    where = f" ({event['location']})" if event.get("location") else ""
    return f"{event['title']} {when}{where}"


class Reminders:
    """Remembers what it already showed, so each event pops up once."""

    def __init__(
        self,
        fetch: Callable[[], list[dict]],
        notify: Callable[[str], None],
        clock: Callable[[], datetime],
    ) -> None:
        self.fetch = fetch
        self.notify = notify
        self.clock = clock
        self.shown: set[str] = set()

    def check(self) -> None:
        try:
            events = self.fetch()
        except (URLError, OSError, ValueError):
            return  # Core offline or an old Core: try again next minute.
        now = self.clock()
        for event in events:
            key = f"{event['id']}@{event['start']}"
            if key in self.shown:
                continue
            self.shown.add(key)
            self.notify(reminder_text(event, now))


def desktop_notifier(tray_notify: Callable[[str, str], None]) -> Callable[[str], None]:
    """Windows: the tray icon's toast. Mac: Notification Center. Linux: notify-send, which every desktop shows."""

    def notify(text: str) -> None:
        if IS_WINDOWS:
            tray_notify(text, "Venus reminder")
            return
        if IS_MAC:
            from venus_node.commands.mac_apps import notify_mac

            notify_mac("Venus reminder", text)
            return
        notify_send = shutil.which("notify-send")
        if notify_send:
            subprocess.run([notify_send, "Venus reminder", text], check=False, timeout=10)
        else:
            tray_notify(text, "Venus reminder")

    return notify


def start_reminders(reminders: Reminders, stop: threading.Event) -> threading.Thread:
    def loop() -> None:
        while not stop.is_set():
            reminders.check()
            stop.wait(CHECK_SECONDS)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread
