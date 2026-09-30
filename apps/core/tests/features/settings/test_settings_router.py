import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from main import app
from storage.base import Base

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_dependencies():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
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
