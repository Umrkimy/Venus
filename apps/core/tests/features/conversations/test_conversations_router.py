from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.conversations.dependencies import get_conversation_repository
from features.conversations.models.conversation import Conversation, Message
from features.conversations.repository import ConversationRepository
from features.projects.dependencies import get_project_repository
from features.projects.repository import ProjectRepository
from main import app
from tests.database import make_test_engine

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

client = TestClient(app)


@pytest.fixture
def engine():
    engine = make_test_engine()
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
    projects = ProjectRepository(engine)
    app.dependency_overrides[get_project_repository] = lambda: projects
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
            {"role": "user", "content": "my name is Umar", "actions": []},
            {"role": "assistant", "content": "Nice to meet you.", "actions": []},
            {"role": "user", "content": "whats my name", "actions": []},
            {"role": "assistant", "content": "Your name is Umar.", "actions": []},
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


def listed_titles(archived: bool = False) -> list[str]:
    response = client.get(
        "/conversations",
        params={"archived": archived},
        headers=OWNER_HEADERS,
    )
    assert response.status_code == 200
    return [row["title"] for row in response.json()]


def test_delete_conversation_removes_it_and_its_messages(engine, conversations):
    deleted = conversations.create("forget this")
    conversations.add_exchange(deleted, "forget this", "Okay.")
    kept = conversations.create("keep this")
    conversations.add_exchange(kept, "keep this", "Sure.")

    response = client.delete(f"/conversations/{deleted}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert listed_titles() == ["keep this"]
    with Session(engine) as session:
        left = session.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == deleted)
        )
    assert left == 0
    assert len(conversations.messages(kept)) == 2


def test_delete_unknown_conversation_returns_404(conversations):
    response = client.delete(f"/conversations/{uuid4()}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_archived_conversation_leaves_main_list_and_shows_in_archive(conversations):
    archived = conversations.create("old plan")
    conversations.create("today")

    response = client.patch(
        f"/conversations/{archived}",
        json={"archived": True},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(archived),
        "archived": True,
        "project_id": None,
    }
    assert listed_titles() == ["today"]
    assert listed_titles(archived=True) == ["old plan"]
    # Archived chats can still be opened.
    opened = client.get(f"/conversations/{archived}", headers=OWNER_HEADERS)
    assert opened.status_code == 200


def test_unarchive_returns_conversation_to_main_list(conversations):
    conversation_id = conversations.create("back again")
    conversations.set_archived(conversation_id, True)

    response = client.patch(
        f"/conversations/{conversation_id}",
        json={"archived": False},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == 200
    assert listed_titles() == ["back again"]
    assert listed_titles(archived=True) == []


def test_archive_unknown_conversation_returns_404(conversations):
    response = client.patch(
        f"/conversations/{uuid4()}",
        json={"archived": True},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_and_archive_require_owner(conversations):
    conversation_id = conversations.create("private")

    assert (
        client.delete(f"/conversations/{conversation_id}").status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert (
        client.patch(
            f"/conversations/{conversation_id}",
            json={"archived": True},
        ).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert conversations.get(conversation_id).archived_at is None


def test_move_conversation_into_and_out_of_project(engine, conversations):
    project = ProjectRepository(engine).create("Java assignment")
    conversation_id = conversations.create("loops question")

    moved_in = client.patch(
        f"/conversations/{conversation_id}",
        json={"project_id": str(project.id)},
        headers=OWNER_HEADERS,
    )
    listed = client.get("/conversations", headers=OWNER_HEADERS).json()
    # Archiving doesn't send project_id, so the chat stays in its project.
    client.patch(
        f"/conversations/{conversation_id}",
        json={"archived": True},
        headers=OWNER_HEADERS,
    )
    still_in = conversations.get(conversation_id).project_id
    moved_out = client.patch(
        f"/conversations/{conversation_id}",
        json={"project_id": None},
        headers=OWNER_HEADERS,
    )

    assert moved_in.json()["project_id"] == str(project.id)
    assert listed[0]["project_id"] == str(project.id)
    assert still_in == project.id
    assert moved_out.status_code == 200
    assert moved_out.json() == {
        "id": str(conversation_id),
        "archived": True,
        "project_id": None,
    }


def test_move_conversation_to_unknown_project_returns_404(conversations):
    conversation_id = conversations.create("lost")

    response = client.patch(
        f"/conversations/{conversation_id}",
        json={"project_id": str(uuid4())},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Project not found"
    assert conversations.get(conversation_id).project_id is None


def test_move_chat_into_archived_project_is_rejected(engine, conversations):
    projects = ProjectRepository(engine)
    project = projects.create("Old")
    projects.set_archived(project.id, True)
    conversation_id = conversations.create("misplaced")

    response = client.patch(
        f"/conversations/{conversation_id}",
        json={"project_id": str(project.id)},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Project is archived"
    assert conversations.get(conversation_id).project_id is None


def test_get_conversation_returns_saved_actions(conversations):
    conversation_id = conversations.create("open spotify")
    action = {"kind": "command", "command_id": "abc", "label": "Spotify"}
    conversations.add_exchange(conversation_id, "open spotify", "Opening it.", [action])

    response = client.get(f"/conversations/{conversation_id}", headers=OWNER_HEADERS)

    assert response.json()["messages"][1]["actions"] == [action]
