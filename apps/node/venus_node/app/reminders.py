"""Calendar reminders: a pop-up on the PC about 10 minutes before each event,
and Venus says it out loud when her voice is on and she isn't busy.

Core knows the calendar; the tray app asks it once a minute what starts
soon and shows each event once. Nothing runs when no calendar is connected
(Core just answers an empty list).
"""

import json
import shutil
import subprocess
import threading
from collections.abc import Callable
from http.client import HTTPException
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


def spoken_text(event: dict, now: datetime) -> str:
    """The same reminder as a sentence Venus says."""
    start = datetime.fromisoformat(event["start"])
    minutes = max(0, round((start - now.astimezone(start.tzinfo)).total_seconds() / 60))
    if minutes == 0:
        text = f"Heads up, {event['title']} is starting now"
    else:
        text = f"Heads up, {event['title']} starts in {minutes} minute{'' if minutes == 1 else 's'}"
    where = f", in {event['location']}" if event.get("location") else ""
    return text + where + "."


class Reminders:
    """Remembers what it already showed, so each event pops up once."""

    def __init__(
        self,
        fetch: Callable[[], list[dict]],
        notify: Callable[[str], None],
        clock: Callable[[], datetime],
        say: Callable[[str], None] | None = None,
    ) -> None:
        self.fetch = fetch
        self.notify = notify
        self.clock = clock
        # Venus's voice; None when it's off on this PC.
        self.say = say
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
            if self.say is not None:
                self.say(spoken_text(event, now))


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


def voice_sayer(settings: NodeSettings, status, muted: threading.Event) -> Callable[[str], None]:
    """Says a reminder with Venus's voice, unless the mic is muted or she's mid-conversation."""
    from venus_node.voice.core_client import speak_stream
    from venus_node.voice.player import play_pcm
    from venus_node.voice.status import IDLE, SPEAKING

    def say(text: str) -> None:
        # Muted means "leave me alone"; a running conversation keeps its turn.
        if muted.is_set() or status.report()[0] != IDLE:
            return
        try:
            rate, pieces = speak_stream(settings, text)
            play_pcm(pieces, rate, on_start=lambda: status.set(SPEAKING, text))
        except (OSError, HTTPException) as exc:
            # HTTPException: the voice stream broke halfway.
            print("Couldn't say the reminder:", exc)
        finally:
            if status.report()[0] == SPEAKING:
                status.set(IDLE)

    return say


def start_reminders(reminders: Reminders, stop: threading.Event) -> threading.Thread:
    def loop() -> None:
        while not stop.is_set():
            reminders.check()
            stop.wait(CHECK_SECONDS)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread
