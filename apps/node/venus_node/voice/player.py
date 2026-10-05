from collections.abc import Callable, Iterable
from threading import Event

SAMPLE_BYTES = 2  # 16-bit mono


def even_pieces(pieces: Iterable[bytes]) -> Iterable[bytes]:
    """Network pieces can split a sample in half; carry the odd byte to the next piece."""
    leftover = b""
    for piece in pieces:
        data = leftover + piece
        cut = len(data) - len(data) % SAMPLE_BYTES
        leftover = data[cut:]
        if cut:
            yield data[:cut]


def play_pcm(
    pieces: Iterable[bytes],
    rate: int,
    on_start: Callable[[], None] | None = None,
    open_output: Callable | None = None,
    stop: Event | None = None,
) -> None:
    """Play Luna's voice on the PC speakers as it arrives.

    Returns when she has finished, or as soon as `stop` is set.
    """
    if open_output is None:
        # Imported here so tests and the connect command don't need audio libraries.
        import sounddevice as sd

        def open_output():
            return sd.RawOutputStream(samplerate=rate, channels=1, dtype="int16")

    started = False
    with open_output() as speakers:
        for piece in even_pieces(pieces):
            if stop is not None and stop.is_set():
                # Drop the queued sound too: silent now, not after the buffer plays out.
                speakers.abort()
                return
            if not started:
                started = True
                if on_start is not None:
                    on_start()
            # Blocks while the speaker buffer is full; closing waits for the rest to play.
            speakers.write(piece)
