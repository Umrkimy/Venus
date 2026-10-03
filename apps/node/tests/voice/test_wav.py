import io
import wave

from venus_node.voice.wav import to_wav


def test_to_wav_writes_16k_mono_header():
    pcm = b"\x01\x00" * 1600

    with wave.open(io.BytesIO(to_wav(pcm)), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16000
        assert wav.readframes(wav.getnframes()) == pcm
