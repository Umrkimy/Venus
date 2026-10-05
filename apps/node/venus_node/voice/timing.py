import time
from collections.abc import Callable


class Timer:
    """Seconds per step of one voice turn, so the log shows where the wait goes."""

    def __init__(self, clock: Callable[[], float] = time.perf_counter) -> None:
        self.clock = clock
        self.last = clock()
        self.steps: list[str] = []

    def lap(self, step: str) -> None:
        now = self.clock()
        self.steps.append(f"{step} {now - self.last:.1f} s")
        self.last = now

    def report(self) -> str:
        return "Timing: " + ", ".join(self.steps)
