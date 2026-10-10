import time
from collections.abc import Callable
from dataclasses import dataclass

IDLE = "idle"

# The web asks every 0.4 s while its tab is in front; a bit longer covers a slow request.
WEB_WATCHING_FOR = 1.2
# The Node reports every 0.5 s; quiet for longer means it closed or crashed.
NODE_ALIVE_FOR = 5.0


@dataclass(frozen=True)
class Seen:
    """What the web gets: the PC's voice loop right now."""

    state: str
    subtitle: str
    muted: bool
    online: bool  # False: no voice loop on the PC (closed, crashed, or not started).
    conversation_id: str | None  # The chat voice turns go into, for the web to open.


@dataclass(frozen=True)
class Reply:
    """What the Node gets back for each report."""

    web_watching: bool  # A Venus tab is in front, so the PC's orb hides.
    web_listening: bool  # That tab listens with the browser mic, so the PC skips "Hey Venus".
    stop: bool  # The web's stop button: cut Luna off, once.


class LiveVoice:
    """What the PC's voice loop is doing right now, and what the web wants from it.

    Kept in memory, not the database: it changes twice a second and is
    worthless after a restart.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.state = IDLE
        self.subtitle = ""
        self.muted = False
        self.reported_at = float("-inf")
        self.watched_at = float("-inf")
        self.web_listening = False
        self.stop_wish = False
        self.conversation_id: str | None = None
        self.mics: list[str] = []

    def report(self, state: str, subtitle: str, muted: bool, mics: list[str] | None = None) -> Reply:
        """The Node's latest state; the answer carries a stop wish, once."""
        self.state = state
        self.subtitle = subtitle
        self.muted = muted
        self.mics = mics or []
        self.reported_at = self.clock()
        stop, self.stop_wish = self.stop_wish, False
        watching = self.clock() - self.watched_at < WEB_WATCHING_FOR
        return Reply(watching, watching and self.web_listening, stop)

    def watch(self, listening: bool = False) -> Seen:
        """The web's poll: remembers the tab is watching, and if it listens itself."""
        self.watched_at = self.clock()
        self.web_listening = listening
        if self.clock() - self.reported_at > NODE_ALIVE_FOR:
            return Seen(IDLE, "", False, False, self.conversation_id)
        return Seen(self.state, self.subtitle, self.muted, True, self.conversation_id)

    def current_mics(self) -> list[str]:
        """The PC's mics, or none once its voice loop stopped reporting."""
        if self.clock() - self.reported_at > NODE_ALIVE_FOR:
            return []
        return self.mics

    def wish_stop(self) -> None:
        """The web's stop button; the Node picks it up on its next report."""
        self.stop_wish = True

    def voice_chat(self, conversation_id: str) -> None:
        """A voice line was just saved in this chat."""
        self.conversation_id = conversation_id


live_voice = LiveVoice()


def get_live_voice() -> LiveVoice:
    return live_voice
