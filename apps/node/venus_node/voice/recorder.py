from collections.abc import Callable, Iterable

import numpy as np


def is_quiet(frame: np.ndarray, level: int = 500) -> bool:
    # Floats first: squaring int16 samples overflows.
    loudness = np.sqrt(np.mean(frame.astype(np.float64) ** 2))
    return loudness < level


def record_until_silence(
    frames: Iterable[np.ndarray],
    quiet_frames: int | Callable[[], int] = 9,
    max_frames: int = 125,
    start_frames: int = 40,
) -> bytes:
    """Keep frames until about 0.7 s of quiet (9 x 80 ms) or 10 seconds.

    `quiet_frames` can be a function, asked each frame: after "uh" you get longer.

    Before you start talking it waits longer (40 x 80 ms, about 3 s): people
    pause after "Hey Venus", and stopping then sent only silence to Core.
    """
    kept: list[np.ndarray] = []
    quiet_in_a_row = 0
    talking = False
    for frame in frames:
        kept.append(frame)
        if is_quiet(frame):
            quiet_in_a_row += 1
        else:
            # A short pause mid-sentence starts the count again.
            quiet_in_a_row = 0
            talking = True
        end = quiet_frames() if callable(quiet_frames) else quiet_frames
        limit = end if talking else start_frames
        if quiet_in_a_row >= limit or len(kept) >= max_frames:
            break
    return b"".join(frame.tobytes() for frame in kept)


def heard_speech(pcm: bytes, frame_size: int = 1280) -> bool:
    """Any loud frame at all? All quiet means nobody spoke: nothing to send."""
    samples = np.frombuffer(pcm, dtype=np.int16)
    return any(
        not is_quiet(samples[i : i + frame_size]) for i in range(0, len(samples), frame_size)
    )


def trim_silence(pcm: bytes, frame_size: int = 1280, pad: int = 3) -> bytes:
    """Drop the quiet start and end, keeping `pad` frames (240 ms) each side.

    Less audio to upload and transcribe. All quiet: unchanged, so Core can say it heard nothing.
    """
    samples = np.frombuffer(pcm, dtype=np.int16)
    frames = [samples[i : i + frame_size] for i in range(0, len(samples), frame_size)]
    loud = [i for i, frame in enumerate(frames) if not is_quiet(frame)]
    if not loud:
        return pcm
    first = max(loud[0] - pad, 0)
    last = min(loud[-1] + pad, len(frames) - 1)
    return b"".join(frame.tobytes() for frame in frames[first : last + 1])
