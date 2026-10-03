import asyncio
from types import SimpleNamespace

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from openai import OpenAIError
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.models.site_shortcut import SiteShortcut
from features.shortcuts.repository import ShortcutRepository
from features.voice.dependencies import get_transcriber
from features.voice.router import MAX_AUDIO_BYTES
from features.voice.transcriber import TRANSCRIBE_MODEL, OpenAITranscriber
from main import app
from storage.base import Base

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}
WEBM = {"Content-Type": "audio/webm"}

client = TestClient(app)


class FakeTranscriber:
    """Hears the same words every time and remembers what it was sent."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[bytes, str, str]] = []

    async def transcribe(self, audio: bytes, content_type: str, hint: str) -> str:
        self.calls.append((audio, content_type, hint))
        if self.error is not None:
            raise self.error
        return "open spotify"


def settings(llm_provider: str = "fake", llm_api_key: str = "") -> CoreSettings:
    return CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
    )


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    app.dependency_overrides[get_settings] = settings
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_settings_repository] = lambda: SettingsRepository(engine)
    app.dependency_overrides[get_shortcut_repository] = lambda: ShortcutRepository(engine)
    yield engine
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def transcriber(engine) -> FakeTranscriber:
    fake = FakeTranscriber()
    app.dependency_overrides[get_transcriber] = lambda: fake
    return fake


def test_transcribe_returns_text(transcriber: FakeTranscriber):
    response = client.post(
        "/voice/transcribe", content=b"audio", headers={**OWNER_HEADERS, **WEBM},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "open spotify"}
    audio, content_type, hint = transcriber.calls[0]
    assert audio == b"audio"
    assert content_type == "audio/webm"
    assert hint.startswith("Venus")


def test_transcribe_hints_saved_shortcuts(transcriber: FakeTranscriber, engine):
    ShortcutRepository(engine).add(
        SiteShortcut(keyword="comix", label="Comix", home_url="https://comix.to/", search_url=None),
    )

    client.post("/voice/transcribe", content=b"audio", headers={**OWNER_HEADERS, **WEBM})

    assert "comix" in transcriber.calls[0][2]


def test_transcribe_needs_owner(transcriber: FakeTranscriber):
    response = client.post("/voice/transcribe", content=b"audio", headers=WEBM)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert transcriber.calls == []


def test_transcribe_rejects_empty_audio(transcriber: FakeTranscriber):
    response = client.post(
        "/voice/transcribe", content=b"", headers={**OWNER_HEADERS, **WEBM},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert transcriber.calls == []


def test_transcribe_rejects_big_audio(transcriber: FakeTranscriber):
    response = client.post(
        "/voice/transcribe",
        content=b"x" * (MAX_AUDIO_BYTES + 1),
        headers={**OWNER_HEADERS, **WEBM},
    )

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert transcriber.calls == []


def test_transcribe_api_error_gives_502(engine):
    app.dependency_overrides[get_transcriber] = lambda: FakeTranscriber(OpenAIError("boom"))

    response = client.post(
        "/voice/transcribe", content=b"audio", headers={**OWNER_HEADERS, **WEBM},
    )

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "boom" not in response.text


def test_transcribe_without_openai_key_gives_503(engine):
    # No fake transcriber: the real dependency sees the fake chat provider.
    response = client.post(
        "/voice/transcribe", content=b"audio", headers={**OWNER_HEADERS, **WEBM},
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["detail"] == "Voice needs an OpenAI API key"


def test_transcribe_with_openai_key_builds_openai_transcriber(engine):
    repository = SettingsRepository(engine)
    transcriber = get_transcriber(settings("openai", "sk-test"), repository)

    assert isinstance(transcriber, OpenAITranscriber)


class FakeTranscriptions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text="  open spotify  ")


def test_openai_transcriber_sends_audio_and_model():
    transcriptions = FakeTranscriptions()
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=transcriptions))
    transcriber = OpenAITranscriber(client)

    text = asyncio.run(
        transcriber.transcribe(b"audio", "audio/webm;codecs=opus", "Venus, comix"),
    )

    assert text == "open spotify"
    assert transcriptions.calls == [
        {
            # The file name tells the API it's webm.
            "file": ("speech.webm", b"audio", "audio/webm;codecs=opus"),
            "model": TRANSCRIBE_MODEL,
            "prompt": "Venus, comix",
        },
    ]
