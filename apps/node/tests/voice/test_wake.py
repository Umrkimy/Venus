import json

import numpy as np

from venus_node.voice.wake import (
    DECOYS,
    WakeListener,
    grammar,
    has_phrase,
    wake_model_path,
)

FRAME = np.zeros(1280, dtype=np.int16)
PHRASES = ["hey venus", "venus", "hey love"]


class FakeRecognizer:
    """Plays back Vosk answers: ("partial", text) or ("final", text) per frame."""

    def __init__(self, answers: list[tuple[str, str]]) -> None:
        self.answers = iter(answers)
        self.current = ("partial", "")
        self.resets = 0

    def AcceptWaveform(self, data):
        self.current = next(self.answers)
        return self.current[0] == "final"

    def PartialResult(self):
        return json.dumps({"partial": self.current[1]})

    def Result(self):
        return json.dumps({"text": self.current[1]})

    def Reset(self):
        self.resets += 1


def hearings(answers: list[tuple[str, str]], hold_frames: int = 5) -> list[bool]:
    listener = WakeListener(FakeRecognizer(answers), PHRASES, hold_frames)
    return [listener.heard(FRAME) for _ in answers]


def test_wake_listener_wakes_when_phrase_holds_for_hold_frames():
    answers = [("partial", "hey")] + [("partial", "hey venus")] * 5

    assert hearings(answers) == [False, False, False, False, False, True]


def test_wake_listener_ignores_a_flickering_guess():
    # Real trace: "hey, what is the weather" guessed "hey love" for 3 frames.
    answers = [("partial", "hey")] + [("partial", "hey love")] * 3 + [("partial", "hey [unk]")] * 3

    assert not any(hearings(answers))


def test_wake_listener_counts_phrase_followed_by_more_words():
    answers = [("partial", "hey venus")] * 2 + [("partial", "hey venus [unk]")] * 3

    assert hearings(answers)[-1]


def test_wake_listener_trusts_a_final_result_at_once():
    assert hearings([("final", "venus [unk]")]) == [True]
    assert hearings([("final", "venice [unk]")]) == [False]


def test_wake_listener_reset_clears_recognizer_and_count():
    recognizer = FakeRecognizer([("partial", "venus")] * 8)
    listener = WakeListener(recognizer, PHRASES, hold_frames=5)
    for _ in range(4):
        listener.heard(FRAME)

    listener.reset()

    assert recognizer.resets == 1
    assert [listener.heard(FRAME) for _ in range(4)] == [False] * 4


def test_has_phrase_matches_whole_words_anywhere():
    assert has_phrase("hey venus [unk]", PHRASES)
    assert has_phrase("[unk] hey venus [unk]", PHRASES)  # talk ran into it
    assert has_phrase("venus", PHRASES)
    assert not has_phrase("venice [unk]", PHRASES)
    assert not has_phrase("hey babe", PHRASES)
    assert not has_phrase("i love you", PHRASES)


def test_grammar_lists_phrases_decoys_and_unknown():
    assert json.loads(grammar(PHRASES)) == PHRASES + DECOYS + ["[unk]"]


def test_wake_model_path_relative_to_node_folder_or_absolute(tmp_path):
    assert wake_model_path(tmp_path, "models/vosk") == tmp_path / "models" / "vosk"
    absolute = tmp_path / "elsewhere" / "vosk"
    assert wake_model_path(tmp_path, str(absolute)) == absolute
