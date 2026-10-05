from collections.abc import Iterable

import numpy as np


def is_quiet(frame: np.ndarray, level: int = 500) -> bool:
    # Floats first: squaring int16 samples overflows.
    loudness = np.sqrt(np.mean(frame.astype(np.float64) ** 2))
    return loudness < level


def record_until_silence(
    frames: Iterable[np.ndarray],
    quiet_frames: int = 12,
    max_frames: int = 125,
    start_frames: int = 40,
) -> bytes:
    """Keep frames until about a second of quiet (12 x 80 ms) or 10 seconds.

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
        limit = quiet_frames if talking else start_frames
        if quiet_in_a_row >= limit or len(kept) >= max_frames:
            break
    return b"".join(frame.tobytes() for frame in kept)
