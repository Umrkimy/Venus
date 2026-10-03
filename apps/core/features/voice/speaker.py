from typing import Protocol

import httpx2

FISH_TTS_URL = "https://api.fish.audio/v1/tts"


class Speaker(Protocol):
    async def speak(self, text: str) -> bytes: ...


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

    async def speak(self, text: str) -> bytes:
        body: dict[str, str] = {"text": text, "format": "mp3"}
        if self._voice_id:
            # The voice made on fish.audio; without it Fish picks a default voice.
            body["reference_id"] = self._voice_id
        async with httpx2.AsyncClient(transport=self._transport, timeout=30) as client:
            response = await client.post(
                FISH_TTS_URL,
                json=body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "model": self._model,
                },
            )
            response.raise_for_status()
            return response.content
