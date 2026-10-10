import json

import numpy as np

from venus_node.voice.live_words import LiveWords, captioned, end_frames, still_thinking
from venus_node.voice.status import LISTENING, THINKING, Status

FRAME = np.zeros(1280, dtype=np.int16)


class FakeVosk:
    """Plays back Vosk answers: ("guess", text) while you talk, ("piece", text) at a pause."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.now = None
        self.resets = 0

    def AcceptWaveform(self, data):
        self.now = self.answers.pop(0)
        return self.now[0] == "piece"

    def Result(self):
        return json.dumps({"text": self.now[1]})

    def PartialResult(self):
        return json.dumps({"partial": self.now[1]})

    def Reset(self):
        self.resets += 1


def test_live_words_keep_finished_pieces_and_add_the_guess():
    words = LiveWords(FakeVosk([("guess", "open"), ("piece", "open spotify"), ("guess", "and play")]))

    seen = [words.hear(FRAME) for _ in range(3)]

    # Vosk starts a new guess after a short pause; the first piece must stay on screen.
    assert seen == ["open", "open spotify", "open spotify and play"]


def test_live_words_reset_starts_a_new_sentence():
    vosk = FakeVosk([("piece", "hello"), ("guess", "bye")])
    words = LiveWords(vosk)
    words.hear(FRAME)

    words.reset()

    assert vosk.resets == 1
    assert words.hear(FRAME) == "bye"


def test_captioned_shows_your_words_while_listening():
    status = Status()
    status.set(LISTENING)
    words = LiveWords(FakeVosk([("guess", "open"), ("guess", "open spotify")]))

    passed = list(captioned([FRAME, FRAME], words, status))

    # Frames go on unchanged to the recorder.
    assert len(passed) == 2
    assert status.report() == (LISTENING, "open spotify")


def test_captioned_without_live_words_just_passes_frames():
    status = Status()
    status.set(LISTENING)

    assert len(list(captioned([FRAME, FRAME], None, status))) == 2
    assert status.report() == (LISTENING, "")


def test_your_words_never_cover_lunas_line():
    status = Status()
    status.set(THINKING)

    status.set_heard("open spotify")

    assert status.report() == (THINKING, "")


def test_still_thinking_after_fillers_and_linking_words():
    assert still_thinking("open spotify and")
    assert still_thinking("play some uh")
    assert not still_thinking("open spotify")
    assert not still_thinking("")


def test_end_wait_doubles_while_you_are_still_thinking():
    status = Status()
    status.set(LISTENING)
    status.set_heard("open spotify and")

    assert end_frames(status) == 38  # 2 x 19 frames.

    status.set_heard("open spotify and play music")

    assert end_frames(status) == 19
