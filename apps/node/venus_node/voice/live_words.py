import json
from collections.abc import Iterable, Iterator

import numpy as np

from venus_node.voice.status import Status

# After these you're still thinking: wait twice as long (same lists as the web).
FILLERS = {"uh", "uhh", "uhm", "um", "umm", "er", "erm", "hmm", "hm", "ah", "eh"}
LINKS = {"and", "but", "so", "or", "like", "because", "cause", "then", "the", "a", "to", "with", "if"}
THINKING_TIMES = 2


def still_thinking(words: str) -> bool:
    """Your words so far end in "uh", "and", "so"...: more is coming."""
    last = words.lower().split()[-1:] or [""]
    return last[0] in FILLERS or last[0] in LINKS


def end_frames(status: Status) -> int:
    """Quiet frames that end your sentence: the Settings pause, twice after "uh"."""
    frames = status.end_pause_frames
    return frames * THINKING_TIMES if still_thinking(status.report()[1]) else frames


class LiveWords:
    """Your words while you talk, from Vosk's free-text guess.

    Only a preview under the orb: the sentence Luna gets still comes from
    Core's transcribe, which is more accurate and knows your shortcut names.
    """

    def __init__(self, recognizer) -> None:
        # The Vosk recognizer is passed in, so tests can use a fake.
        self._recognizer = recognizer
        # Vosk closes a piece at each short pause and starts the next guess empty.
        self._said = ""

    def reset(self) -> None:
        self._recognizer.Reset()
        self._said = ""

    def hear(self, frame: np.ndarray) -> str:
        if self._recognizer.AcceptWaveform(frame.tobytes()):
            piece = json.loads(self._recognizer.Result())["text"]
            self._said = f"{self._said} {piece}".strip()
            return self._said
        guess = json.loads(self._recognizer.PartialResult())["partial"]
        return f"{self._said} {guess}".strip()


def captioned(frames: Iterable[np.ndarray], words: LiveWords | None, status: Status) -> Iterator[np.ndarray]:
    """Pass frames through, showing what Vosk thinks you're saying."""
    # A plain loop, not "yield from": when the recorder stops early this
    # wrapper is closed, and "yield from" would close the shared mic frames too.
    if words is not None:
        words.reset()
    for frame in frames:
        if words is not None:
            status.set_heard(words.hear(frame))
        yield frame
