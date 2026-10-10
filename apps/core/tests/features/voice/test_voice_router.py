import asyncio
from types import SimpleNamespace

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from openai import OpenAIError

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.models.site_shortcut import SiteShortcut
from features.shortcuts.repository import ShortcutRepository
from features.usage.dependencies import get_usage_repository
from features.usage.repository import UsageRepository
from features.voice.dependencies import get_transcriber
from features.voice.router import MAX_AUDIO_BYTES, NOTHING_HEARD
from features.voice.transcriber import TRANSCRIBE_MODEL, OpenAITranscriber, is_hint_echo
from main import app
from tests.database import make_test_engine

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
    engine = make_test_engine()
    app.dependency_overrides[get_settings] = settings
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_settings_repository] = lambda: SettingsRepository(engine)
    app.dependency_overrides[get_usage_repository] = lambda: UsageRepository(engine)
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


def test_transcribe_spells_shortcuts_like_the_owner(engine):
    ShortcutRepository(engine).add(
        SiteShortcut(keyword="comix", label="Comix", home_url="https://comix.to/", search_url=None),
    )
    app.dependency_overrides[get_transcriber] = lambda: HeardTranscriber(
        "Search comics for Solo Leveling.",
    )

    response = client.post(
        "/voice/transcribe", content=b"audio", headers={**OWNER_HEADERS, **WEBM},
    )

    assert response.json() == {"text": "Search comix for Solo Leveling."}


def test_transcribe_turns_a_repeated_hint_into_a_mic_problem(engine):
    # Silence makes the model read the hint back; that must not reach the chat box.
    for keyword in ("asurascans", "comix"):
        ShortcutRepository(engine).add(
            SiteShortcut(keyword=keyword, label=keyword, home_url=f"https://{keyword}.com/", search_url=None),
        )
    app.dependency_overrides[get_transcriber] = lambda: HeardTranscriber("Venus, asurascans, comix")

    response = client.post(
        "/voice/transcribe", content=b"audio", headers={**OWNER_HEADERS, **WEBM},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": NOTHING_HEARD}


def test_is_hint_echo_only_matches_the_whole_hint():
    hint = "Venus, asurascans, comix"

    assert is_hint_echo("Venus, asurascans, comix.", hint)
    assert is_hint_echo("venus asurascans comix", hint)
    assert not is_hint_echo("Open comix.", hint)
    assert not is_hint_echo("comix", hint)
    assert not is_hint_echo("", hint)


class HeardTranscriber:
    """Hears whatever sentence the test gives it."""

    def __init__(self, text: str) -> None:
        self.text = text

    async def transcribe(self, audio: bytes, content_type: str, hint: str) -> str:
        return self.text


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
    usage = UsageRepository(engine)
    transcriber = get_transcriber(settings("openai", "sk-test"), repository, usage)

    assert isinstance(transcriber, OpenAITranscriber)
    assert transcriber._usage is usage


class FakeTranscriptions:
    def __init__(self, usage=None) -> None:
        self.calls: list[dict] = []
        self.usage = usage

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text="  open spotify  ", usage=self.usage)


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


class FakeUsageLog:
    def __init__(self) -> None:
        self.records: list[tuple] = []

    def record(self, kind: str, model: str, usage) -> None:
        self.records.append((kind, model, usage))


def test_openai_transcriber_counts_its_tokens():
    used = SimpleNamespace(input_tokens=40, output_tokens=4)
    transcriptions = FakeTranscriptions(usage=used)
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=transcriptions))
    usage = FakeUsageLog()
    transcriber = OpenAITranscriber(client, usage=usage)

    asyncio.run(transcriber.transcribe(b"audio", "audio/webm", "Venus"))

    assert usage.records == [("transcribe", TRANSCRIBE_MODEL, used)]


def test_transcribe_accepts_the_node_token(transcriber: FakeTranscriber):
    # "Hey Venus" on the PC sends its recording with the Node's token.
    response = client.post(
        "/voice/transcribe",
        content=b"audio",
        headers={"Authorization": "Bearer test-node-token", **WEBM},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "open spotify"}
