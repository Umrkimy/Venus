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
) -> bytes:
    """Keep frames until about a second of quiet (12 x 80 ms) or 10 seconds."""
    kept: list[np.ndarray] = []
    quiet_in_a_row = 0
    for frame in frames:
        kept.append(frame)
        # A short pause mid-sentence starts the count again.
        quiet_in_a_row = quiet_in_a_row + 1 if is_quiet(frame) else 0
        if quiet_in_a_row >= quiet_frames or len(kept) >= max_frames:
            break
    return b"".join(frame.tobytes() for frame in kept)
