import math
from collections.abc import Iterable, Iterator
from threading import Lock

import numpy as np

IDLE = "idle"
LISTENING = "listening"
THINKING = "thinking"
SPEAKING = "speaking"
SLEEPING = "sleeping"  # Shown briefly to confirm "stop listening".

# Loudness of a normal speaking voice into a headset mic is about 2000-3000.
LOUD = 2500.0


class Status:
    """What the voice loop is doing, shared with the circle window.

    The voice loop runs in a background thread and the window in the main
    thread, so both sides go through this lock.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._state = IDLE
        self._level = 0.0
        self._closed = False

    def set(self, state: str) -> None:
        with self._lock:
            self._state = state
            if state != LISTENING:
                self._level = 0.0

    def set_level(self, level: float) -> None:
        with self._lock:
            # Smooth it, or the orb jitters on every 80 ms frame (but still follows syllables).
            self._level = 0.4 * self._level + 0.6 * level

    def snapshot(self) -> tuple[str, float]:
        with self._lock:
            return self._state, self._level

    def close(self) -> None:
        with self._lock:
            self._closed = True

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
