from uuid import UUID

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.personalities.dependencies import get_personality_repository
from features.personalities.repository import PersonalityRepository
from main import app
from storage.base import Base

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

client = TestClient(app)


@pytest.fixture
def personalities():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repository = PersonalityRepository(engine)
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_personality_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()
    engine.dispose()


def test_activating_a_personality_switches_the_other_off(personalities):
    personal = personalities.create("Personal", "Be flirty.")
    professional = personalities.create("Professional", "Be polite.")
    personalities.activate(personal.id)

    response = client.patch(
        f"/personalities/{professional.id}",
        json={"active": True},
        headers=OWNER_HEADERS,
    )

    listed = client.get("/personalities", headers=OWNER_HEADERS).json()

    assert response.status_code == status.HTTP_200_OK
    assert [(row["name"], row["active"]) for row in listed] == [
        ("Personal", False),
        ("Professional", True),
    ]


def test_active_personality_cannot_be_deleted(personalities):
    personal = personalities.create("Personal", "Be flirty.")
    personalities.activate(personal.id)

    response = client.delete(f"/personalities/{personal.id}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert personalities.get(personal.id) is not None


def test_inactive_personality_can_be_deleted(personalities):
    spare = personalities.create("Spare", "Be quiet.")

    response = client.delete(f"/personalities/{spare.id}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert personalities.get(spare.id) is None


def test_create_personality_rejects_blank_name_or_long_text(personalities):
    blank = client.post(
        "/personalities",
        json={"name": "  ", "text": "Be flirty."},
        headers=OWNER_HEADERS,
    )
    long = client.post(
        "/personalities",
        json={"name": "Long", "text": "x" * 4001},
        headers=OWNER_HEADERS,
    )

    assert blank.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert long.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert personalities.list_all() == []


def test_new_personality_starts_switched_off(personalities):
    response = client.post(
        "/personalities",
        json={"name": " Demo ", "text": "Be formal."},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "Demo"
    assert response.json()["active"] is False
    assert personalities.active() is None
    assert personalities.get(UUID(response.json()["id"])) is not None


def test_personality_routes_require_owner(personalities):
    assert client.get("/personalities").status_code == status.HTTP_401_UNAUTHORIZED
