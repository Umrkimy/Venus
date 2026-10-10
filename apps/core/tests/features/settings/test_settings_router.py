import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.settings.secrets import decrypt_text
from main import app
from tests.database import make_test_engine

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_dependencies():
    engine = make_test_engine()
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_settings_repository] = (
        lambda: SettingsRepository(engine)
    )
    yield
    app.dependency_overrides.clear()
    engine.dispose()


def test_get_mode_defaults_to_confirm():
    response = client.get("/settings/mode", headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"mode": "confirm"}


def test_put_mode_switches_to_full():
    response = client.put(
        "/settings/mode", json={"mode": "full"}, headers=OWNER_HEADERS,
    )

    assert response.status_code == 200
    assert client.get("/settings/mode", headers=OWNER_HEADERS).json() == {
        "mode": "full",
    }


def test_put_mode_rejects_unknown_mode():
    response = client.put(
        "/settings/mode", json={"mode": "yolo"}, headers=OWNER_HEADERS,
    )

    assert response.status_code == 422


def test_put_mode_requires_owner():
    response = client.put("/settings/mode", json={"mode": "full"})

    assert response.status_code == 401


SECRET_KEY = Fernet.generate_key().decode()


def use_settings(**changes):
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
        **changes,
    )


def save_llm(**body):
    return client.put("/settings/llm", json=body, headers=OWNER_HEADERS)


def test_llm_settings_fall_back_to_env():
    use_settings(llm_provider="openai", llm_model="gpt-6-luna", llm_api_key="sk-env")

    response = client.get("/settings/llm", headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "provider": "openai",
        "model": "gpt-6-luna",
        "has_key": True,
    }


def test_llm_settings_never_return_the_key():
    use_settings(secret_key=SECRET_KEY)

    put = save_llm(provider="openai", model="gpt-6-luna", api_key="sk-secret")
    get = client.get("/settings/llm", headers=OWNER_HEADERS)

    expected = {"provider": "openai", "model": "gpt-6-luna", "has_key": True}
    assert put.status_code == 200
    assert put.json() == expected
    assert get.json() == expected
    assert "sk-secret" not in put.text + get.text


def test_llm_settings_store_the_key_encrypted():
    use_settings(secret_key=SECRET_KEY)
    repository = app.dependency_overrides[get_settings_repository]()

    save_llm(provider="openai", model="gpt-6-luna", api_key="sk-secret")
    stored = repository.get_llm().api_key_encrypted

    assert stored != "sk-secret"
    assert "sk-secret" not in stored
    assert decrypt_text(stored, SECRET_KEY) == "sk-secret"


def test_llm_settings_put_without_key_keeps_old_key():
    use_settings(secret_key=SECRET_KEY)
    repository = app.dependency_overrides[get_settings_repository]()
    save_llm(provider="openai", model="gpt-6-luna", api_key="sk-secret")

    response = save_llm(provider="openai", model="gpt-6-mini")
    stored = repository.get_llm()

    assert response.json()["has_key"] is True
    assert stored.model == "gpt-6-mini"
    assert decrypt_text(stored.api_key_encrypted, SECRET_KEY) == "sk-secret"


def test_llm_settings_need_secret_key_for_api_key():
    response = save_llm(provider="openai", model="gpt-6-luna", api_key="sk-secret")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Set VENUS_CORE_SECRET_KEY in Core's .env first",
    }


def test_llm_settings_reject_unknown_provider():
    response = save_llm(provider="skynet", model="t-800")

    assert response.status_code == 422


def test_llm_settings_require_owner():
    get = client.get("/settings/llm")
    put = client.put("/settings/llm", json={"provider": "fake", "model": ""})

    assert get.status_code == 401
    assert put.status_code == 401


def save_voice(**body):
    return client.put("/settings/voice", json=body, headers=OWNER_HEADERS)


def test_voice_settings_fall_back_to_env():
    use_settings(fish_api_key="fish-env", fish_voice_id="voice-env", fish_model="s1")

    response = client.get("/settings/voice", headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"voice_id": "voice-env", "model": "s1", "has_key": True}


def test_voice_settings_never_return_the_key():
    use_settings(secret_key=SECRET_KEY)

    put = save_voice(voice_id=" voice-123 ", model="s2.1-pro-free", api_key="fish-secret")
    get = client.get("/settings/voice", headers=OWNER_HEADERS)

    expected = {"voice_id": "voice-123", "model": "s2.1-pro-free", "has_key": True}
    assert put.status_code == 200
    assert put.json() == expected
    assert get.json() == expected
    assert "fish-secret" not in put.text + get.text


def test_voice_settings_store_the_key_encrypted():
    use_settings(secret_key=SECRET_KEY)
    repository = app.dependency_overrides[get_settings_repository]()

    save_voice(voice_id="voice-123", model="s2.1-pro-free", api_key="fish-secret")
    stored = repository.get_voice().api_key_encrypted

    assert "fish-secret" not in stored
    assert decrypt_text(stored, SECRET_KEY) == "fish-secret"


def test_voice_settings_put_without_key_keeps_old_key():
    use_settings(secret_key=SECRET_KEY)
    repository = app.dependency_overrides[get_settings_repository]()
    save_voice(voice_id="voice-123", model="s2.1-pro-free", api_key="fish-secret")

    response = save_voice(voice_id="voice-456", model="s2.1-pro")
    stored = repository.get_voice()

    assert response.json() == {"voice_id": "voice-456", "model": "s2.1-pro", "has_key": True}
    assert decrypt_text(stored.api_key_encrypted, SECRET_KEY) == "fish-secret"


def test_voice_settings_need_secret_key_for_api_key():
    response = save_voice(voice_id="voice-123", model="s1", api_key="fish-secret")

    assert response.status_code == 409


def test_voice_settings_reject_unknown_model():
    response = save_voice(voice_id="voice-123", model="s9-ultra")

    assert response.status_code == 422


def test_voice_settings_require_owner():
    get = client.get("/settings/voice")
    put = client.put("/settings/voice", json={"voice_id": "", "model": "s1"})

    assert get.status_code == 401
    assert put.status_code == 401


def test_time_settings_start_empty():
    response = client.get("/settings/time", headers=OWNER_HEADERS)

    assert response.status_code == 200
    # No time zone yet: the web offers the browser's own.
    assert response.json() == {"time_zone": None, "country": ""}


def test_time_settings_put_is_remembered():
    response = client.put(
        "/settings/time",
        json={"time_zone": "Asia/Kuala_Lumpur", "country": " Malaysia "},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == 200
    saved = {"time_zone": "Asia/Kuala_Lumpur", "country": "Malaysia"}
    assert response.json() == saved
    assert client.get("/settings/time", headers=OWNER_HEADERS).json() == saved


def test_time_settings_reject_unknown_time_zone():
    response = client.put(
        "/settings/time",
        json={"time_zone": "Mars/Olympus_Mons", "country": ""},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == 422


def test_time_settings_require_owner():
    get = client.get("/settings/time")
    put = client.put("/settings/time", json={"time_zone": "UTC"})

    assert get.status_code == 401
    assert put.status_code == 401


def test_listening_settings_default_to_one_and_a_half_seconds():
    response = client.get("/settings/listening", headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"end_pause_ms": 1500}


def test_listening_settings_put_is_remembered():
    response = client.put("/settings/listening", json={"end_pause_ms": 750}, headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"end_pause_ms": 750}
    assert client.get("/settings/listening", headers=OWNER_HEADERS).json() == {"end_pause_ms": 750}


@pytest.mark.parametrize("end_pause_ms", [250, 3250, 1600])
def test_listening_settings_reject_values_off_the_slider(end_pause_ms: int):
    # Below 0.5 s, above 3 s, or between the quarter-second steps.
    response = client.put(
        "/settings/listening", json={"end_pause_ms": end_pause_ms}, headers=OWNER_HEADERS,
    )

    assert response.status_code == 422


def test_listening_settings_require_owner():
    get = client.get("/settings/listening")
    put = client.put("/settings/listening", json={"end_pause_ms": 1500})

    assert get.status_code == 401
    assert put.status_code == 401
