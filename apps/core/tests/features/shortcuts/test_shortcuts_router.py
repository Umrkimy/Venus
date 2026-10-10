import pytest
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.repository import ShortcutRepository
from main import app
from tests.database import make_test_engine

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}
COMIX = {
    "keyword": "comix",
    "label": "Comix",
    "home_url": "https://comix.to",
    "search_example": "https://comix.to/search?q={words}",
}

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
    app.dependency_overrides[get_shortcut_repository] = (
        lambda: ShortcutRepository(engine)
    )
    yield
    app.dependency_overrides.clear()
    engine.dispose()


def test_add_shortcut_then_list_it():
    response = client.post("/shortcuts", json=COMIX, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_201_CREATED
    # HttpUrl adds the slash after a bare domain.
    assert response.json()["home_url"] == "https://comix.to/"
    assert client.get("/shortcuts", headers=OWNER_HEADERS).json() == {
        "shortcuts": [response.json()],
    }


def test_shortcut_without_search_link_is_saved_with_none():
    response = client.post(
        "/shortcuts",
        json={"keyword": "asura", "label": "Asura", "home_url": "https://asura.gg"},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["search_url"] is None


def test_keyword_is_saved_lowercase():
    response = client.post(
        "/shortcuts", json={**COMIX, "keyword": " Comix "}, headers=OWNER_HEADERS,
    )

    assert response.json()["keyword"] == "comix"


def test_add_duplicate_keyword_is_rejected():
    client.post("/shortcuts", json=COMIX, headers=OWNER_HEADERS)

    response = client.post(
        "/shortcuts", json={**COMIX, "keyword": "COMIX"}, headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "detail": "You already have a shortcut called comix",
    }


@pytest.mark.parametrize("keyword", ["open", "two words", ""])
def test_unusable_keyword_is_rejected(keyword: str):
    response = client.post(
        "/shortcuts", json={**COMIX, "keyword": keyword}, headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_search_example_is_saved_as_template():
    response = client.post(
        "/shortcuts",
        json={**COMIX, "search_example": "https://comix.to/browse?q=solo%20leveling"},
        headers=OWNER_HEADERS,
    )

    assert response.json()["search_url"] == "https://comix.to/browse?q={words}"


def test_search_example_without_search_is_rejected():
    response = client.post(
        "/shortcuts",
        json={**COMIX, "search_example": "https://comix.to/browse"},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() == {
        "detail": "I couldn't find your search in that link. "
        "What did you search for?",
    }


def test_delete_shortcut_removes_it():
    client.post("/shortcuts", json=COMIX, headers=OWNER_HEADERS)

    response = client.delete("/shortcuts/Comix", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert client.get("/shortcuts", headers=OWNER_HEADERS).json() == {
        "shortcuts": [],
    }


def test_delete_missing_shortcut_returns_404():
    response = client.delete("/shortcuts/comix", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_shortcut_changes_fields():
    client.post("/shortcuts", json=COMIX, headers=OWNER_HEADERS)

    response = client.put(
        "/shortcuts/Comix",
        json={"label": "Comix Site", "home_url": "https://comix.to/home"},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "keyword": "comix",
        "label": "Comix Site",
        "home_url": "https://comix.to/home",
        "search_url": None,
    }


def test_update_missing_shortcut_returns_404():
    response = client.put(
        "/shortcuts/comix",
        json={"label": "Comix", "home_url": "https://comix.to"},
        headers=OWNER_HEADERS,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_shortcut_requires_owner():
    response = client.put(
        "/shortcuts/comix",
        json={"label": "Comix", "home_url": "https://comix.to"},
    )

    assert response.status_code == 401


def test_shortcuts_require_owner():
    assert client.get("/shortcuts").status_code == 401
    assert client.post("/shortcuts", json=COMIX).status_code == 401
    assert client.delete("/shortcuts/comix").status_code == 401
