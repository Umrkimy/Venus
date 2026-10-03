import numpy as np


def play_mp3(mp3: bytes) -> None:
    """Play Luna's voice on the PC speakers; returns when she has finished."""
    # Imported here so tests and the connect command don't need audio libraries.
    import miniaudio
    import sounddevice as sd

    sound = miniaudio.decode(mp3, output_format=miniaudio.SampleFormat.SIGNED16)
    samples = np.frombuffer(sound.samples, dtype=np.int16).reshape(-1, sound.nchannels)
    sd.play(samples, sound.sample_rate)
    sd.wait()
