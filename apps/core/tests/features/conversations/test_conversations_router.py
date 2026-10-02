from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.conversations.dependencies import get_conversation_repository
from features.conversations.models.conversation import Conversation
from features.conversations.repository import ConversationRepository
from main import app
from storage.base import Base

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

client = TestClient(app)


@pytest.fixture
def engine():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def conversations(engine):
    repository = ConversationRepository(engine)
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_conversation_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


def set_updated_at(engine, conversation_id, when: datetime) -> None:
    with Session(engine) as session:
        session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=when)
        )
        session.commit()


def test_list_conversations_shows_newest_first(engine, conversations):
    older = conversations.create("plan the 3D avatar")
    newer = conversations.create("what games do I like")
    set_updated_at(engine, older, datetime(2026, 10, 1, tzinfo=timezone.utc))
    set_updated_at(engine, newer, datetime(2026, 10, 2, tzinfo=timezone.utc))

    response = client.get("/conversations", headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert [row["title"] for row in response.json()] == [
        "what games do I like",
        "plan the 3D avatar",
    ]


def test_get_conversation_returns_messages_in_order(conversations):
    conversation_id = conversations.create("my name is Umar")
    conversations.add_exchange(conversation_id, "my name is Umar", "Nice to meet you.")
    conversations.add_exchange(conversation_id, "whats my name", "Your name is Umar.")

    response = client.get(f"/conversations/{conversation_id}", headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "id": str(conversation_id),
        "title": "my name is Umar",
        "messages": [
            {"role": "user", "content": "my name is Umar"},
            {"role": "assistant", "content": "Nice to meet you."},
            {"role": "user", "content": "whats my name"},
            {"role": "assistant", "content": "Your name is Umar."},
        ],
    }


def test_get_unknown_conversation_returns_404(conversations):
    response = client.get(f"/conversations/{uuid4()}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_conversations_require_owner(conversations):
    assert client.get("/conversations").status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        client.get(f"/conversations/{uuid4()}").status_code
        == status.HTTP_401_UNAUTHORIZED
    )


def test_recent_turns_keeps_only_the_newest_in_order(conversations):
    conversation_id = conversations.create("count")
    for number in range(6):
        conversations.add_exchange(conversation_id, f"q{number}", f"a{number}")

    turns = conversations.recent_turns(conversation_id, limit=4)

    assert [turn.content for turn in turns] == ["q4", "a4", "q5", "a5"]
