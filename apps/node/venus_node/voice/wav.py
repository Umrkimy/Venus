import io
import wave


def to_wav(pcm: bytes, rate: int = 16000) -> bytes:
    """Raw 16-bit mono samples plus the header Core's /voice/transcribe reads."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm)
    return buffer.getvalue()
