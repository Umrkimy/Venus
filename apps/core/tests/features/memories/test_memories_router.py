from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.memories.dependencies import get_memory_repository
from features.memories.models.memory import Memory
from features.memories.repository import MemoryRepository
from main import app
from storage.base import Base

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

client = TestClient(app)


def saved_minutes_ago(memories: MemoryRepository, text: str, minutes: int) -> None:
    # Saves in one test can share a timestamp; set clear times instead.
    memory = memories.create(text)
    with Session(memories.engine) as session:
        session.get(Memory, memory.id).created_at = (
            datetime.now(timezone.utc) - timedelta(minutes=minutes)
        )
        session.commit()


@pytest.fixture
def memories():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repository = MemoryRepository(engine)
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_memory_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()
    engine.dispose()


def test_created_memories_are_listed_newest_first(memories):
    saved_minutes_ago(memories, "Owner name is Umar", 5)
    response = client.post(
        "/memories", json={"text": "  Owner likes lo-fi  "}, headers=OWNER_HEADERS,
    )

    listed = client.get("/memories", headers=OWNER_HEADERS).json()

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["text"] == "Owner likes lo-fi"
    assert [row["text"] for row in listed] == ["Owner likes lo-fi", "Owner name is Umar"]


def test_same_fact_in_other_case_is_saved_once(memories):
    first = memories.create("Owner name is Umar")

    response = client.post(
        "/memories", json={"text": "owner name is umar"}, headers=OWNER_HEADERS,
    )

    assert response.json()["id"] == str(first.id)
    assert len(memories.list_all()) == 1


def test_blank_memory_is_rejected(memories):
    response = client.post("/memories", json={"text": "   "}, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert memories.list_all() == []


def test_memory_text_can_be_edited(memories):
    memory = memories.create("Owner likes lo-fi")

    response = client.patch(
        f"/memories/{memory.id}", json={"text": "Owner likes jazz"}, headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_200_OK
    assert memories.get(memory.id).text == "Owner likes jazz"


def test_memory_can_be_deleted(memories):
    memory = memories.create("Owner likes lo-fi")

    response = client.delete(f"/memories/{memory.id}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert memories.get(memory.id) is None


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_unknown_memory_is_not_found(memories, method):
    kwargs = {"json": {"text": "x"}} if method == "patch" else {}

    response = getattr(client, method)(
        f"/memories/{uuid4()}", headers=OWNER_HEADERS, **kwargs,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_newest_keeps_only_the_latest_facts(memories):
    for number in range(3):
        saved_minutes_ago(memories, f"Fact {number}", 10 - number)

    assert [memory.text for memory in memories.newest(2)] == ["Fact 2", "Fact 1"]


def test_memories_require_owner(memories):
    response = client.get("/memories")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
