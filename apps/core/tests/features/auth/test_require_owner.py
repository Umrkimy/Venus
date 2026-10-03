from datetime import datetime, timezone

import pytest
from fastapi import Depends, FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from config import CoreSettings, get_settings
from features.auth.dependencies import (
    SESSION_COOKIE_NAME,
    get_auth_repository,
    require_owner,
    require_owner_or_node,
)
from features.auth.passwords import hash_password
from features.auth.repository import AuthRepository
from storage.base import Base

TEST_OWNER_TOKEN = "test-owner-token"

app = FastAPI()


@app.get("/protected", dependencies=[Depends(require_owner)])
def protected():
    return {"ok": True}


@app.get("/voice-ish", dependencies=[Depends(require_owner_or_node)])
def voice_ish():
    return {"ok": True}


@pytest.fixture
def repository():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield AuthRepository(engine)
    engine.dispose()


@pytest.fixture
def client(repository):
    app.dependency_overrides[get_auth_repository] = lambda: repository
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="sqlite+pysqlite://",
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_valid_session_cookie_is_accepted(client, repository):
    now = datetime.now(timezone.utc)
    owner = repository.create_owner("umar", hash_password("correct horse"), now)
    token = repository.create_session(owner.account_id, now)
    client.cookies.set(SESSION_COOKIE_NAME, token)

    response = client.get("/protected")

    assert response.status_code == status.HTTP_200_OK


def test_dev_owner_token_is_accepted(client):
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_200_OK


def test_wrong_bearer_token_is_rejected(client):
    response = client.get(
        "/protected",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_unknown_session_cookie_is_rejected(client):
    client.cookies.set(SESSION_COOKIE_NAME, "not-a-real-session")

    response = client.get("/protected")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_request_without_credentials_is_rejected(client):
    response = client.get("/protected")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_node_token_is_rejected_on_owner_only_routes(client):
    response = client.get("/protected", headers={"Authorization": "Bearer test-node-token"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("token", ["test-node-token", TEST_OWNER_TOKEN])
def test_owner_or_node_accepts_node_and_owner_tokens(client, token):
    response = client.get("/voice-ish", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == status.HTTP_200_OK


def test_owner_or_node_rejects_other_tokens(client):
    response = client.get("/voice-ish", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
