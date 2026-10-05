from collections.abc import Callable
from functools import partial
from http.client import HTTPException
from threading import Event

from venus_node.config import NodeSettings
from venus_node.voice.core_client import report_state
from venus_node.voice.status import Status

# Twice a second is enough for the web's orb; a state change goes at once.
EVERY = 0.5


def report_loop(
    settings: NodeSettings,
    status: Status,
    muted: Event | None = None,
    send: Callable[[str, str, bool], tuple[bool, bool, bool]] | None = None,
    every: float = EVERY,
) -> None:
    """Keep Core up to date with the orb; learn if a web tab shows it (and
    listens) instead, and stop Luna when the web's stop button asks."""
    muted = muted if muted is not None else Event()
    send = send or partial(report_state, settings)
    while not status.closed:
        # Cleared before reading: a change while we send wakes the next round at once.
        status.changed.clear()
        state, subtitle = status.report()
        try:
            watching, listening, stop = send(state, subtitle, muted.is_set())
        except (OSError, HTTPException, ValueError, KeyError):
            # Core down or restarting: the PC's orb and "Hey Venus" carry on as before.
            watching, listening, stop = False, False, False
        status.set_web_watching(watching)
        status.set_web_listening(listening)
        if stop:
            status.request_stop()
        status.changed.wait(every)
