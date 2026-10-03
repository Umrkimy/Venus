import json
from pathlib import Path

import numpy as np

# Sound-alikes Vosk can pick instead of a wake phrase: it must choose from
# the list, so without them "venice" or "genius" comes out as "venus".
DECOYS = ["venice", "genius", "hey babe", "babe", "i love you", "love", "hey"]


def grammar(phrases: list[str]) -> str:
    """The only words Vosk may hear; anything else is [unk]."""
    return json.dumps(phrases + DECOYS + ["[unk]"])


def has_phrase(text: str, phrases: list[str]) -> bool:
    # Whole words anywhere: talk running into it gives "[unk] hey venus [unk]";
    # "venice" doesn't count.
    words = text.split()
    for phrase in phrases:
        target = phrase.split()
        if any(words[i:i + len(target)] == target for i in range(len(words))):
            return True
    return False


class WakeListener:
    """Says whether one mic frame finished a wake phrase."""

    def __init__(self, recognizer, phrases: list[str], hold_frames: int = 5) -> None:
        # The Vosk recognizer is passed in, so tests can use a fake.
        self._recognizer = recognizer
        self._phrases = phrases
        self._hold_frames = hold_frames
        self._held = 0

    def heard(self, frame: np.ndarray) -> bool:
        if self._recognizer.AcceptWaveform(frame.tobytes()):
            # Vosk is sure the sentence ended: trust it right away.
            self._held = 0
            text = json.loads(self._recognizer.Result())["text"]
            return has_phrase(text, self._phrases)
        # A guess while still talking can flicker ("hey, what" -> "hey love"
        # for 3 frames); a real phrase stays, so wait until it holds.
        text = json.loads(self._recognizer.PartialResult())["partial"]
        self._held = self._held + 1 if has_phrase(text, self._phrases) else 0
        return self._held >= self._hold_frames

    def reset(self) -> None:
        # Without this the same phrase fires again on the next frames.
        self._recognizer.Reset()
        self._held = 0


def wake_model_path(node_directory: Path, setting: str) -> Path:
    # A relative setting like models/vosk-model-small-en-us-0.15 lives next to the Node code.
    path = Path(setting)
    return path if path.is_absolute() else node_directory / path
