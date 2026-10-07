from datetime import datetime, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from features.auth import router as auth_router
from features.auth.dependencies import SESSION_COOKIE_NAME, get_auth_repository
from features.auth.passwords import hash_password
from features.auth.rate_limit import LoginRateLimiter, get_login_rate_limiter
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
    limiter = LoginRateLimiter()
    app.dependency_overrides[get_auth_repository] = lambda: repository
    app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
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


def test_login_cookie_not_secure_on_localhost(client):
    response = client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
    )

    assert "Secure" not in response.headers["set-cookie"]


def test_login_cookie_secure_over_https(client):
    # Tailscale and Next pass the scheme along as "https,http".
    response = client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
        headers={"X-Forwarded-Proto": "https,http"},
    )

    assert "Secure" in response.headers["set-cookie"]


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


def test_login_rejects_too_long_username(client):
    response = client.post(
        "/auth/login",
        json={"username": "u" * 101, "password": "correct horse"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_login_rejects_too_long_password(client):
    response = client.post(
        "/auth/login",
        json={"username": "umar", "password": "p" * 1025},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_login_verifies_password_for_unknown_username(client, monkeypatch):
    calls = []

    def spy_verify_password(password, password_hash_value):
        calls.append(password_hash_value)
        return False

    monkeypatch.setattr(auth_router, "verify_password", spy_verify_password)

    response = client.post(
        "/auth/login",
        json={"username": "nobody", "password": "correct horse"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert calls == [auth_router._DUMMY_HASH]


def test_login_blocks_after_five_failures(client):
    for _ in range(5):
        response = client.post(
            "/auth/login",
            json={"username": "umar", "password": "wrong password"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    response = client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.json() == {"detail": "Too many login attempts"}


def test_successful_login_resets_failure_count(client):
    for _ in range(4):
        client.post(
            "/auth/login",
            json={"username": "umar", "password": "wrong password"},
        )
    client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
    )

    for _ in range(4):
        client.post(
            "/auth/login",
            json={"username": "umar", "password": "wrong password"},
        )
    response = client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
    )

    assert response.status_code == status.HTTP_200_OK


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


def test_login_failures_count_per_forwarded_client(client):
    phone = {"X-Forwarded-For": "100.64.0.2"}
    for _ in range(5):
        client.post(
            "/auth/login",
            json={"username": "umar", "password": "wrong password"},
            headers=phone,
        )

    blocked = client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
        headers=phone,
    )
    other_device = client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
        headers={"X-Forwarded-For": "100.64.0.3"},
    )

    assert blocked.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert other_device.status_code == status.HTTP_200_OK


def test_login_rate_limit_uses_last_forwarded_entry(client):
    # Only the last entry comes from our own proxy; earlier ones can be faked.
    for fake in range(5):
        client.post(
            "/auth/login",
            json={"username": "umar", "password": "wrong password"},
            headers={"X-Forwarded-For": f"6.6.6.{fake}, 100.64.0.2"},
        )

    response = client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
        headers={"X-Forwarded-For": "100.64.0.2"},
    )

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_login_cookie_lasts_thirty_days(client):
    response = client.post(
        "/auth/login",
        json={"username": "umar", "password": "correct horse"},
    )

    assert "Max-Age=2592000" in response.headers["set-cookie"]
