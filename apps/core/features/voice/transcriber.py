from typing import Protocol

from openai import AsyncOpenAI

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
    def __init__(self, client: AsyncOpenAI, model: str = TRANSCRIBE_MODEL) -> None:
        self._client = client
        self._model = model

    async def transcribe(self, audio: bytes, content_type: str, hint: str) -> str:
        extension = EXTENSIONS.get(content_type.split(";")[0].strip(), "webm")
        result = await self._client.audio.transcriptions.create(
            file=(f"speech.{extension}", audio, content_type),
            model=self._model,
            # Names like Spotify or comix, so they come back spelled right.
            prompt=hint,
        )
        return result.text.strip()
