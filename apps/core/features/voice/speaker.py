from collections.abc import AsyncIterator
from typing import Protocol

import httpx2

FISH_TTS_URL = "https://api.fish.audio/v1/tts"

# Streamed voice is raw 16-bit mono PCM at this rate: the PC plays each piece as it lands.
SAMPLE_RATE = 44100


class Speaker(Protocol):
    async def speak(self, text: str) -> bytes: ...

    def stream(self, text: str) -> AsyncIterator[bytes]: ...


class FishSpeaker:
    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model: str,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._model = model
        # Tests pass a fake transport so nothing goes to Fish.
        self._transport = transport

    def _body(self, text: str, audio_format: str) -> dict[str, str | int]:
        body: dict[str, str | int] = {"text": text, "format": audio_format}
        if self._voice_id:
            # The voice made on fish.audio; without it Fish picks a default voice.
            body["reference_id"] = self._voice_id
        return body

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "model": self._model}

    async def speak(self, text: str) -> bytes:
        async with httpx2.AsyncClient(transport=self._transport, timeout=30) as client:
            response = await client.post(
                FISH_TTS_URL, json=self._body(text, "mp3"), headers=self._headers(),
            )
            response.raise_for_status()
            return response.content

    async def stream(self, text: str) -> AsyncIterator[bytes]:
        """Luna's voice in pieces as Fish makes them (first audio in under a second)."""
        body = self._body(text, "pcm")
        body["sample_rate"] = SAMPLE_RATE
        # Fish's faster setting: a little less polish, sooner first audio.
        body["latency"] = "balanced"
        async with httpx2.AsyncClient(transport=self._transport, timeout=30) as client:
            async with client.stream(
                "POST", FISH_TTS_URL, json=body, headers=self._headers(),
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    yield chunk
