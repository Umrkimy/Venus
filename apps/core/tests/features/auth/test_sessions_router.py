from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.passwords import hash_password
from features.auth.rate_limit import LoginRateLimiter, get_login_rate_limiter
from features.auth.repository import AuthRepository
from main import app
from storage.base import Base

IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Version/18.0 Mobile Safari/604.1"
WINDOWS = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36"


@pytest.fixture
def repository():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    repository = AuthRepository(engine)
    repository.create_owner("umar", hash_password("correct horse"), datetime.now(timezone.utc))
    limiter = LoginRateLimiter()
    app.dependency_overrides[get_auth_repository] = lambda: repository
    app.dependency_overrides[get_login_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token="test-owner-token",
        database_url="sqlite+pysqlite://",
    )
    yield repository
    app.dependency_overrides.clear()
    engine.dispose()


def browser(user_agent: str) -> TestClient:
    """A separate browser with its own cookie jar, logged in."""
    client = TestClient(app, headers={"User-Agent": user_agent})
    response = client.post("/auth/login", json={"username": "umar", "password": "correct horse"})
    assert response.status_code == status.HTTP_200_OK
    return client


def test_each_login_shows_up_with_its_browser(repository):
    pc = browser(WINDOWS)
    browser(IPHONE)

    sessions = pc.get("/auth/sessions").json()

    assert {s["user_agent"] for s in sessions} == {WINDOWS, IPHONE}
    assert [s["user_agent"] for s in sessions if s["current"]] == [WINDOWS]
    assert all(s["last_seen_at"] for s in sessions)
    # Only the public id goes out, never the token or its hash.
    assert "token_hash" not in sessions[0]


def test_signing_out_a_browser_ends_its_login(repository):
    pc = browser(WINDOWS)
    phone = browser(IPHONE)
    phone_id = next(s["id"] for s in pc.get("/auth/sessions").json() if not s["current"])

    response = pc.delete(f"/auth/sessions/{phone_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert phone.get("/auth/me").status_code == status.HTTP_401_UNAUTHORIZED
    assert pc.get("/auth/me").status_code == status.HTTP_200_OK


def test_sign_out_others_keeps_only_this_browser(repository):
    pc = browser(WINDOWS)
    phone = browser(IPHONE)
    mac = browser("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) Safari/605.1.15")

    response = pc.post("/auth/sessions/sign-out-others")

    assert response.json() == {"signed_out": 2}
    assert phone.get("/auth/me").status_code == status.HTTP_401_UNAUTHORIZED
    assert mac.get("/auth/me").status_code == status.HTTP_401_UNAUTHORIZED
    assert pc.get("/auth/me").status_code == status.HTTP_200_OK


def test_sessions_need_the_owner(repository):
    client = TestClient(app)

    assert client.get("/auth/sessions").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.post("/auth/sessions/sign-out-others").status_code == status.HTTP_401_UNAUTHORIZED


def test_unknown_session_is_404(repository):
    pc = browser(WINDOWS)

    response = pc.delete("/auth/sessions/00000000-0000-0000-0000-000000000000")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_last_seen_is_saved_at_most_every_five_minutes(repository):
    start = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)
    owner = repository.get_owner_by_username("umar")
    token = repository.create_session(owner.account_id, start, IPHONE)

    repository.get_owner_for_session(token, start + timedelta(minutes=2))
    first = repository.list_sessions(start)[0].last_seen_at
    repository.get_owner_for_session(token, start + timedelta(minutes=6))
    second = repository.list_sessions(start)[0].last_seen_at

    assert first.replace(tzinfo=timezone.utc) == start
    assert second.replace(tzinfo=timezone.utc) == start + timedelta(minutes=6)


def test_expired_logins_are_not_listed(repository):
    long_ago = datetime(2026, 1, 1, tzinfo=timezone.utc)
    owner = repository.get_owner_by_username("umar")
    repository.create_session(owner.account_id, long_ago, IPHONE)

    assert repository.list_sessions(datetime.now(timezone.utc)) == []
