import re
from typing import Protocol

from openai import AsyncOpenAI

from features.usage.repository import UsageLog

# Small, cheap model for short spoken commands; change here to try another.
TRANSCRIBE_MODEL = "gpt-4o-mini-transcribe"

# The SDK finds the format from the file name, so give each type an extension.
EXTENSIONS = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "mp4",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
}


class Transcriber(Protocol):
    async def transcribe(self, audio: bytes, content_type: str, hint: str) -> str: ...


class OpenAITranscriber:
    def __init__(
        self, client: AsyncOpenAI, model: str = TRANSCRIBE_MODEL, usage: UsageLog | None = None,
    ) -> None:
        self._client = client
        self._model = model
        self._usage = usage

    async def transcribe(self, audio: bytes, content_type: str, hint: str) -> str:
        extension = EXTENSIONS.get(content_type.split(";")[0].strip(), "webm")
        result = await self._client.audio.transcriptions.create(
            file=(f"speech.{extension}", audio, content_type),
            model=self._model,
            # Names like Spotify or comix, so they come back spelled right.
            prompt=hint,
        )
        if self._usage is not None:
            self._usage.record("transcribe", self._model, getattr(result, "usage", None))
        return result.text.strip()


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def is_hint_echo(text: str, hint: str) -> bool:
    """True when the model only repeated the hint back.

    With silence (no mic, a muted mic, a virtual mic) it often returns the
    prompt word for word: "Venus, asurascans, comix".
    """
    heard = _words(text)
    return bool(heard) and heard == _words(hint)
