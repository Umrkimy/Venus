from datetime import datetime, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from features.auth.dependencies import SESSION_COOKIE_NAME, get_auth_repository
from features.auth.passwords import hash_password
from features.auth.repository import AuthRepository
from main import app
from storage.base import Base


@pytest.fixture
def repository():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repository = AuthRepository(engine)
    repository.create_owner(
        "umar",
        hash_password("correct horse"),
        datetime.now(timezone.utc),
    )
    yield repository
    engine.dispose()


@pytest.fixture
def client(repository):
    app.dependency_overrides[get_auth_repository] = lambda: repository
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_login_sets_http_only_session_cookie(client):
    response = client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"username": "umar"}
    assert "HttpOnly" in response.headers["set-cookie"]


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/auth/login",
        json={"username": "umar", "password": "wrong password"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid username or password"}


def test_login_rejects_unknown_username(client):
    response = client.post(
        "/auth/login",
        json={"username": "nobody", "password": "correct horse"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Invalid username or password"}


def test_me_returns_owner_with_valid_cookie(client):
    client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
    )

    response = client.get("/auth/me")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"username": "umar"}


def test_me_rejects_missing_cookie(client):
    response = client.get("/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not logged in"}


def test_logout_invalidates_session(client, repository):
    client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
    )
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert token is not None

    response = client.post("/auth/logout")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert repository.get_owner_for_session(token, datetime.now(timezone.utc)) is None