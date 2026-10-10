import math
from collections.abc import Iterable, Iterator
from threading import Event, Lock

import numpy as np

IDLE = "idle"
LISTENING = "listening"
THINKING = "thinking"
SPEAKING = "speaking"
SLEEPING = "sleeping"  # Shown briefly to confirm "stop listening".

# Loudness of a normal speaking voice into a headset mic is about 2000-3000.
LOUD = 2500.0

# Until Core says otherwise (Settings -> Voice): wait 1.5 s after you stop talking.
DEFAULT_END_PAUSE_MS = 1500
FRAME_MS = 80


class Status:
    """What the voice loop is doing, shared with the circle window and Core.

    The voice loop, the window and the Core reporter run in different
    threads, so all of them go through this lock.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = IDLE
        self._level = 0.0
        self._subtitle = ""
        self._web_watching = False
        self._web_listening = False
        self._closed = False
        self._end_pause_ms = DEFAULT_END_PAUSE_MS
        self._mic = ""  # Settings mic list; "" = not picked there.
        self._mic_in_use = ""
        # "Stop talking" (web button, tray, "stop venus"): cut Luna off or drop her answer.
        self.stop = Event()
        # Wakes the Core reporter at once, instead of on its next tick.
        self.changed = Event()

    def set(self, state: str, subtitle: str = "") -> None:
        """New state; `subtitle` is Luna's line while she speaks."""
        with self._lock:
            self._state = state
            self._subtitle = subtitle
            if state != LISTENING:
                self._level = 0.0
        self.changed.set()

    def set_heard(self, words: str) -> None:
        """Your words so far while you talk, shown where Luna's line goes."""
        with self._lock:
            # Not after you stop: thinking and speaking have their own line.
            if self._state == LISTENING:
                self._subtitle = words

    def set_level(self, level: float) -> None:
        with self._lock:
            # Smooth it, or the orb jitters on every 80 ms frame (but still follows syllables).
            self._level = 0.4 * self._level + 0.6 * level

    def snapshot(self) -> tuple[str, float]:
        with self._lock:
            return self._state, self._level

    def report(self) -> tuple[str, str]:
        """State and subtitle, what Core passes on to the web."""
        with self._lock:
            return self._state, self._subtitle

    def set_web_watching(self, watching: bool) -> None:
        with self._lock:
            self._web_watching = watching

    def set_web_listening(self, listening: bool) -> None:
        with self._lock:
            self._web_listening = listening

    @property
    def web_listening(self) -> bool:
        """That tab listens with the browser mic, so "Hey Venus" here pauses."""
        with self._lock:
            return self._web_listening

    def set_end_pause_ms(self, end_pause_ms: int) -> None:
        with self._lock:
            self._end_pause_ms = end_pause_ms

    @property
    def end_pause_frames(self) -> int:
        """Quiet mic frames in a row that end your sentence (the Settings slider)."""
        with self._lock:
            return max(round(self._end_pause_ms / FRAME_MS), 1)

    def set_mic(self, mic: str) -> None:
        with self._lock:
            self._mic = mic

    def wanted_mic(self, fallback: str) -> str:
        """The mic picked in Settings, else `fallback` (VENUS_NODE_MIC in .env)."""
        with self._lock:
            return self._mic or fallback

    def use_mic(self, mic: str) -> None:
        with self._lock:
            self._mic_in_use = mic

    @property
    def mic_in_use(self) -> str:
        with self._lock:
            return self._mic_in_use

    def request_stop(self) -> None:
        self.stop.set()

    @property
    def web_watching(self) -> bool:
        """A Venus tab is in front and shows the orb, so the PC's orb hides."""
        with self._lock:
            return self._web_watching

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.changed.set()

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed


def loudness_level(frame: np.ndarray) -> float:
    """0 for silence, 1 for a loud voice."""
    # Floats first: squaring int16 samples overflows.
    loudness = np.sqrt(np.mean(frame.astype(np.float64) ** 2))
    # Square root: soft talking still moves the orb, shouting doesn't max it out at once.
    return min(math.sqrt(float(loudness) / LOUD), 1.0)


def metered(frames: Iterable[np.ndarray], status: Status) -> Iterator[np.ndarray]:
    """Pass frames through, telling the circle how loud each one is."""
    for frame in frames:
        status.set_level(loudness_level(frame))
        yield frame
