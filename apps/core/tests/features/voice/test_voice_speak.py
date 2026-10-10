import asyncio
import json

import httpx2
import pytest
from cryptography.fernet import Fernet
from fastapi import status
from fastapi.testclient import TestClient

from config import FISH_MODEL, CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.settings.secrets import encrypt_text
from features.voice.dependencies import get_speaker, voice_choice
from features.voice.router import MAX_SPEAK_CHARS
from features.voice.speaker import FISH_TTS_URL, SAMPLE_RATE, FishSpeaker
from main import app
from tests.database import make_test_engine

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

client = TestClient(app)


class FakeSpeaker:
    """Returns the same audio every time and remembers what it was asked to say."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[str] = []

    async def speak(self, text: str) -> bytes:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return b"mp3-bytes"

    async def stream(self, text: str):
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        for piece in (b"pcm-1", b"pcm-2"):
            yield piece


SECRET_KEY = Fernet.generate_key().decode()


def settings(fish_api_key: str = "", **changes) -> CoreSettings:
    return CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
        fish_api_key=fish_api_key,
        **changes,
    )


@pytest.fixture
def engine():
    engine = make_test_engine()
    app.dependency_overrides[get_settings] = lambda: settings()
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_settings_repository] = lambda: SettingsRepository(engine)
    yield engine
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def speaker(engine) -> FakeSpeaker:
    fake = FakeSpeaker()
    app.dependency_overrides[get_speaker] = lambda: fake
    return fake


def test_speak_returns_audio(speaker: FakeSpeaker):
    response = client.post("/voice/speak", json={"text": " hi babe "}, headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert response.content == b"mp3-bytes"
    # Spaces around the line aren't sent.
    assert speaker.calls == ["hi babe"]


def test_speak_needs_owner(speaker: FakeSpeaker):
    response = client.post("/voice/speak", json={"text": "hi"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert speaker.calls == []


def test_speak_empty_text_is_422(speaker: FakeSpeaker):
    response = client.post("/voice/speak", json={"text": "   "}, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert speaker.calls == []


def test_speak_too_long_is_413(speaker: FakeSpeaker):
    text = "a" * (MAX_SPEAK_CHARS + 1)

    response = client.post("/voice/speak", json={"text": text}, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert speaker.calls == []


def test_speak_fish_error_is_502(engine):
    app.dependency_overrides[get_speaker] = lambda: FakeSpeaker(httpx2.HTTPError("boom"))

    response = client.post("/voice/speak", json={"text": "hi"}, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "boom" not in response.text


def test_speak_without_fish_key_is_503(engine):
    # No fake speaker: the real dependency sees no Fish key in settings.
    response = client.post("/voice/speak", json={"text": "hi"}, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Voice reply needs a Fish Audio key"


def test_speak_with_fish_key_builds_fish_speaker(engine):
    speaker = get_speaker(settings("fish-test"), SettingsRepository(engine))

    assert isinstance(speaker, FishSpeaker)


def fish_transport(requests: list[httpx2.Request]) -> httpx2.MockTransport:
    def handle(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, content=b"mp3-bytes")

    return httpx2.MockTransport(handle)


def test_fish_speaker_sends_key_voice_and_model():
    requests: list[httpx2.Request] = []
    speaker = FishSpeaker("fish-test", "voice-123", FISH_MODEL, fish_transport(requests))

    audio = asyncio.run(speaker.speak("hi babe"))

    assert audio == b"mp3-bytes"
    request = requests[0]
    assert str(request.url) == FISH_TTS_URL
    assert request.headers["authorization"] == "Bearer fish-test"
    assert request.headers["model"] == FISH_MODEL
    assert json.loads(request.content) == {
        "text": "hi babe",
        "format": "mp3",
        "reference_id": "voice-123",
    }


def test_fish_speaker_without_voice_lets_fish_pick():
    requests: list[httpx2.Request] = []
    speaker = FishSpeaker("fish-test", "", FISH_MODEL, fish_transport(requests))

    asyncio.run(speaker.speak("hi"))

    assert "reference_id" not in json.loads(requests[0].content)


def test_fish_speaker_raises_on_fish_error():
    def handle(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(402, json={"message": "no credit"})

    speaker = FishSpeaker("fish-test", "", FISH_MODEL, httpx2.MockTransport(handle))

    with pytest.raises(httpx2.HTTPError):
        asyncio.run(speaker.speak("hi"))


def test_voice_choice_uses_env_when_nothing_saved(engine):
    env = settings("fish-env", fish_voice_id="voice-env", fish_model="s1")

    assert voice_choice(env, SettingsRepository(engine)) == ("fish-env", "voice-env", "s1")


def test_voice_choice_prefers_saved_settings(engine):
    repository = SettingsRepository(engine)
    repository.set_voice("voice-web", "s2.1-pro", encrypt_text("fish-web", SECRET_KEY))
    env = settings("fish-env", fish_voice_id="voice-env", secret_key=SECRET_KEY)

    assert voice_choice(env, repository) == ("fish-web", "voice-web", "s2.1-pro")


def test_voice_choice_keeps_env_key_when_none_saved(engine):
    repository = SettingsRepository(engine)
    repository.set_voice("voice-web", FISH_MODEL, None)

    assert voice_choice(settings("fish-env"), repository) == ("fish-env", "voice-web", FISH_MODEL)


def test_speak_stream_sends_pieces_with_the_sample_rate(speaker: FakeSpeaker):
    response = client.post("/voice/speak/stream", json={"text": " hi "}, headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/pcm"
    assert response.headers["x-sample-rate"] == str(SAMPLE_RATE)
    assert response.content == b"pcm-1pcm-2"
    assert speaker.calls == ["hi"]


def test_speak_stream_fish_error_is_502_before_any_audio(engine):
    app.dependency_overrides[get_speaker] = lambda: FakeSpeaker(httpx2.HTTPError("boom"))

    response = client.post("/voice/speak/stream", json={"text": "hi"}, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY


def test_speak_stream_checks_text_like_speak(speaker: FakeSpeaker):
    response = client.post("/voice/speak/stream", json={"text": "  "}, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert speaker.calls == []


def test_fish_speaker_stream_asks_for_fast_raw_pcm():
    requests: list[httpx2.Request] = []
    speaker = FishSpeaker("fish-test", "voice-123", FISH_MODEL, fish_transport(requests))

    async def collect():
        return b"".join([chunk async for chunk in speaker.stream("hi babe")])

    assert asyncio.run(collect()) == b"mp3-bytes"
    assert json.loads(requests[0].content) == {
        "text": "hi babe",
        "format": "pcm",
        "reference_id": "voice-123",
        "sample_rate": SAMPLE_RATE,
        "latency": "balanced",
    }
