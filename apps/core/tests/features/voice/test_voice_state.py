import pytest
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.voice.live import LiveVoice, get_live_voice
from main import app
from tests.database import make_test_engine

OWNER_HEADERS = {"Authorization": "Bearer test-owner-token"}
NODE_HEADERS = {"Authorization": "Bearer test-node-token"}

client = TestClient(app)


class Clock:
    """A clock the test moves by hand."""

    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def live(clock: Clock) -> LiveVoice:
    fake = LiveVoice(clock)
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token="test-owner-token",
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    # A throwaway database for logins: without it the real one (and .env) is used,
    # which CI doesn't have.
    engine = make_test_engine()
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_live_voice] = lambda: fake
    yield fake
    app.dependency_overrides.clear()
    engine.dispose()


def report(state: str = "listening", subtitle: str = "", muted: bool = False) -> dict:
    response = client.put(
        "/voice/state", json={"state": state, "subtitle": subtitle, "muted": muted}, headers=NODE_HEADERS,
    )
    return response.json()


def test_web_sees_what_the_node_reported(live: LiveVoice):
    report("speaking", "hi babe")

    response = client.get("/voice/state", headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "state": "speaking", "subtitle": "hi babe", "muted": False, "online": True, "conversation_id": None,
    }
    # A browser must not reuse an old answer.
    assert response.headers["cache-control"] == "no-store"


def test_node_hears_web_is_watching_only_while_it_polls(live: LiveVoice, clock: Clock):
    assert report()["web_watching"] is False

    client.get("/voice/state", headers=OWNER_HEADERS)
    clock.now += 1.0
    assert report()["web_watching"] is True

    # Tab hidden or closed: polls stop, the PC orb comes back.
    clock.now += 1.0
    assert report()["web_watching"] is False


def test_quiet_node_reads_as_offline(live: LiveVoice, clock: Clock):
    report("speaking", "hi")
    clock.now += 6.0

    assert client.get("/voice/state", headers=OWNER_HEADERS).json() == {
        "state": "idle", "subtitle": "", "muted": False, "online": False, "conversation_id": None,
    }


def test_web_stop_reaches_the_node_once(live: LiveVoice):
    report("speaking", "hi")
    response = client.post("/voice/stop", headers=OWNER_HEADERS)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert report("speaking", "hi")["stop"] is True
    # Delivered: the next turn isn't cut off too.
    assert report("speaking", "hi")["stop"] is False


def test_node_skips_hey_venus_while_the_web_listens(live: LiveVoice, clock: Clock):
    client.get("/voice/state", params={"listening": "true"}, headers=OWNER_HEADERS)
    assert report()["web_listening"] is True

    # Mic off in the web: the PC listens for "Hey Venus" again.
    client.get("/voice/state", headers=OWNER_HEADERS)
    assert report()["web_listening"] is False

    # Tab closed while listening: polls stop, so the PC takes over again.
    client.get("/voice/state", params={"listening": "true"}, headers=OWNER_HEADERS)
    clock.now += 2.0
    assert report()["web_listening"] is False


def test_unknown_state_is_422(live: LiveVoice):
    response = client.put("/voice/state", json={"state": "dancing"}, headers=NODE_HEADERS)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_voice_state_needs_owner_or_node(live: LiveVoice):
    assert client.get("/voice/state").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.put("/voice/state", json={"state": "idle"}).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.post("/voice/stop").status_code == status.HTTP_401_UNAUTHORIZED
