from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.conversations.repository import ConversationRepository
from features.projects.dependencies import get_project_repository
from features.projects.repository import ProjectRepository
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
def projects(engine):
    repository = ProjectRepository(engine)
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_project_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()


def test_create_and_list_projects(projects):
    created = client.post(
        "/projects",
        json={"name": "  Java assignment  "},
        headers=OWNER_HEADERS,
    )

    listed = client.get("/projects", headers=OWNER_HEADERS)

    assert created.status_code == status.HTTP_201_CREATED
    assert created.json()["name"] == "Java assignment"
    assert [(row["id"], row["name"]) for row in listed.json()] == [
        (created.json()["id"], "Java assignment"),
    ]


def test_create_project_rejects_blank_or_long_name(projects):
    blank = client.post("/projects", json={"name": "   "}, headers=OWNER_HEADERS)
    long = client.post("/projects", json={"name": "x" * 61}, headers=OWNER_HEADERS)

    assert blank.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert long.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert projects.list_all() == []


def test_rename_project(projects):
    project = projects.create("Assignmnet")

    response = client.patch(
        f"/projects/{project.id}",
        json={"name": "Assignment"},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Assignment"
    assert projects.get(project.id).name == "Assignment"


def test_rename_unknown_project_returns_404(projects):
    response = client.patch(
        f"/projects/{uuid4()}",
        json={"name": "Nothing"},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_project_deletes_its_chats_and_messages(engine, projects):
    project = projects.create("Venus")
    conversations = ConversationRepository(engine)
    inside = conversations.create("plan the sidebar", project.id)
    conversations.add_exchange(inside, "plan the sidebar", "Projects first.")
    outside = conversations.create("unrelated")

    response = client.delete(f"/projects/{project.id}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert projects.list_all() == []
    assert conversations.get(inside) is None
    assert conversations.messages(inside) == []
    assert conversations.get(outside) is not None
    assert client.delete(
        f"/projects/{project.id}", headers=OWNER_HEADERS,
    ).status_code == status.HTTP_404_NOT_FOUND


def test_delete_project_also_deletes_archived_chats(engine, projects):
    project = projects.create("Venus")
    conversations = ConversationRepository(engine)
    archived = conversations.create("old idea", project.id)
    conversations.set_archived(archived, True)

    client.delete(f"/projects/{project.id}", headers=OWNER_HEADERS)

    assert conversations.get(archived) is None


def test_project_json_counts_its_chats(engine, projects):
    project = projects.create("Venus")
    projects.create("Empty")
    conversations = ConversationRepository(engine)
    conversations.create("one", project.id)
    archived = conversations.create("two", project.id)
    conversations.set_archived(archived, True)
    conversations.create("loose")

    listed = client.get("/projects", headers=OWNER_HEADERS).json()

    counts = {row["name"]: row["chat_count"] for row in listed}
    assert counts == {"Venus": 2, "Empty": 0}


def test_archive_project_hides_it_from_list_and_shows_in_archived(projects):
    kept = projects.create("Kept")
    project = projects.create("Old")

    response = client.patch(
        f"/projects/{project.id}",
        json={"archived": True},
        headers=OWNER_HEADERS,
    )
    active = client.get("/projects", headers=OWNER_HEADERS).json()
    archived = client.get("/projects?archived=true", headers=OWNER_HEADERS).json()

    assert response.status_code == 200
    assert response.json()["archived"] is True
    assert response.json()["name"] == "Old"
    assert [row["id"] for row in active] == [str(kept.id)]
    assert [row["id"] for row in archived] == [str(project.id)]


def test_unarchive_project_brings_it_back(projects):
    project = projects.create("Old")
    projects.set_archived(project.id, True)

    response = client.patch(
        f"/projects/{project.id}",
        json={"archived": False},
        headers=OWNER_HEADERS,
    )
    active = client.get("/projects", headers=OWNER_HEADERS).json()

    assert response.json()["archived"] is False
    assert [row["id"] for row in active] == [str(project.id)]


def test_projects_require_owner(projects):
    project = projects.create("Private")

    assert client.get("/projects").status_code == status.HTTP_401_UNAUTHORIZED
    assert (
        client.post("/projects", json={"name": "x"}).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert (
        client.patch(f"/projects/{project.id}", json={"name": "y"}).status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert (
        client.delete(f"/projects/{project.id}").status_code
        == status.HTTP_401_UNAUTHORIZED
    )
    assert projects.get(project.id).name == "Private"
