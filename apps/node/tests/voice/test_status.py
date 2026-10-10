import numpy as np

from venus_node.voice.status import (
    IDLE,
    LISTENING,
    SPEAKING,
    THINKING,
    Status,
    loudness_level,
    metered,
)


def test_loudness_level_is_zero_for_silence_and_capped_at_one():
    assert loudness_level(np.zeros(1280, dtype=np.int16)) == 0.0
    assert loudness_level(np.full(1280, 30000, dtype=np.int16)) == 1.0


def test_metered_passes_frames_through_and_reports_loudness():
    status = Status()
    loud = np.full(1280, 3000, dtype=np.int16)

    out = list(metered([loud, loud], status))

    assert len(out) == 2 and out[0] is loud
    assert status.snapshot()[1] > 0.5


def test_level_resets_when_listening_ends():
    status = Status()
    status.set(LISTENING)
    status.set_level(1.0)

    status.set(THINKING)

    assert status.snapshot() == (THINKING, 0.0)


def test_close_is_seen_by_the_window():
    status = Status()
    assert not status.closed

    status.close()

    assert status.closed


def test_subtitle_shows_only_with_its_line():
    status = Status()
    status.set(SPEAKING, "hi babe")
    assert status.report() == (SPEAKING, "hi babe")

    status.set(IDLE)
    assert status.report() == (IDLE, "")


def test_set_and_close_wake_the_reporter():
    status = Status()
    status.set(SPEAKING, "hi")
    assert status.changed.is_set()

    status.changed.clear()
    status.close()
    assert status.changed.is_set()


def test_end_pause_frames_follow_the_settings_slider():
    status = Status()
    # Default 1.5 s: about 19 frames of 80 ms.
    assert status.end_pause_frames == 19

    status.set_end_pause_ms(500)

    assert status.end_pause_frames == 6
