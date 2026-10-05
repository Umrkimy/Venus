import numpy as np

from venus_node.voice.recorder import heard_speech, is_quiet, record_until_silence, trim_silence

QUIET = np.full(1280, 10, dtype=np.int16)
LOUD = np.full(1280, 5000, dtype=np.int16)


def test_is_quiet_true_for_low_frame_false_for_loud():
    assert is_quiet(QUIET)
    assert not is_quiet(LOUD)


def test_record_until_silence_stops_after_quiet_run():
    frames = iter([LOUD, LOUD] + [QUIET] * 3 + [LOUD] * 5)

    pcm = record_until_silence(frames, quiet_frames=3)

    # Two loud frames, then the three quiet ones that ended it.
    assert pcm == b"".join(f.tobytes() for f in [LOUD, LOUD, QUIET, QUIET, QUIET])
    assert next(frames) is LOUD  # the rest is left for wake listening


def test_record_until_silence_loud_frame_resets_quiet_count():
    frames = [LOUD, QUIET, QUIET, LOUD, QUIET, QUIET, QUIET]

    pcm = record_until_silence(iter(frames), quiet_frames=3)

    assert len(pcm) == len(frames) * LOUD.nbytes


def test_record_until_silence_stops_at_max_frames():
    pcm = record_until_silence(iter([LOUD] * 50), max_frames=5)

    assert len(pcm) == 5 * LOUD.nbytes


def test_record_until_silence_waits_for_you_to_start_talking():
    # A pause after "Hey Venus" longer than the end-of-sentence quiet.
    frames = [QUIET] * 5 + [LOUD, LOUD] + [QUIET] * 3

    pcm = record_until_silence(iter(frames), quiet_frames=3, start_frames=8)

    assert len(pcm) == len(frames) * LOUD.nbytes


def test_record_until_silence_gives_up_if_you_never_talk():
    frames = iter([QUIET] * 20)

    pcm = record_until_silence(frames, quiet_frames=3, start_frames=8)

    assert len(pcm) == 8 * QUIET.nbytes


def test_trim_silence_keeps_speech_plus_a_little_quiet_each_side():
    frames = [QUIET] * 6 + [LOUD, LOUD] + [QUIET] * 5
    pcm = b"".join(f.tobytes() for f in frames)

    trimmed = trim_silence(pcm, pad=2)

    assert trimmed == b"".join(f.tobytes() for f in [QUIET, QUIET, LOUD, LOUD, QUIET, QUIET])


def test_trim_silence_leaves_all_quiet_audio_alone():
    pcm = QUIET.tobytes() * 4

    assert trim_silence(pcm) == pcm



def test_heard_speech_only_when_something_was_loud():
    quiet = np.zeros(1280 * 3, dtype=np.int16).tobytes()
    loud = np.full(1280, 3000, dtype=np.int16).tobytes()

    assert heard_speech(quiet) is False
    assert heard_speech(quiet + loud) is True
