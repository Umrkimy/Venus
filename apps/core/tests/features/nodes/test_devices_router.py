from contextlib import contextmanager

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.commands.dependencies import get_command_record_repository
from features.commands.repository import CommandRecordRepository
from features.nodes.connection_registry import (
    NodeConnectionRegistry,
    get_connection_registry,
)
from main import app
from storage.base import Base

ENV_TOKEN = "test-node-token"
OWNER_HEADERS = {"Authorization": "Bearer test-owner-token"}

client = TestClient(app)


@pytest.fixture(autouse=True)
def overrides():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token=ENV_TOKEN,
        dev_owner_token="test-owner-token",
        database_url="sqlite+pysqlite://",
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_command_record_repository] = (
        lambda: CommandRecordRepository(engine)
    )
    app.dependency_overrides[get_connection_registry] = lambda: registry
    yield registry
    app.dependency_overrides.clear()
    engine.dispose()


@contextmanager
def connected(token: str, device_id: str):
    with client.websocket_connect(
        "/nodes/connect", headers={"Authorization": f"Bearer {token}"}
    ) as websocket:
        websocket.send_json({"device_id": device_id})
        yield websocket


def add_device(name: str = "Laptop") -> dict:
    response = client.post("/devices", json={"name": name}, headers=OWNER_HEADERS)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_new_device_token_is_shown_once():
    created = add_device()

    listed = client.get("/devices", headers=OWNER_HEADERS).json()

    assert len(created["token"]) >= 40
    assert [device["id"] for device in listed] == [created["id"]]
    assert "token" not in listed[0]
    assert "token_hash" not in listed[0]


def test_new_device_token_connects_and_shows_online():
    token = add_device()["token"]

    with connected(token, "laptop-1") as websocket:
        assert websocket.receive_json() == {"device_id": "laptop-1"}
        device = client.get("/devices", headers=OWNER_HEADERS).json()[0]

    assert device["device_id"] == "laptop-1"
    assert device["connected"] is True
    assert device["last_seen_at"] is not None


def test_token_cannot_pose_as_another_device():
    token = add_device()["token"]
    with connected(token, "laptop-1") as websocket:
        websocket.receive_json()

    with connected(token, "pc-umar") as websocket:
        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()

    assert error.value.code == status.WS_1008_POLICY_VIOLATION


def test_env_token_shows_up_as_the_main_pc():
    with connected(ENV_TOKEN, "pc-umar") as websocket:
        websocket.receive_json()

    devices = client.get("/devices", headers=OWNER_HEADERS).json()

    assert [(d["name"], d["device_id"], d["main"]) for d in devices] == [
        ("Main PC", "pc-umar", True)
    ]


def test_main_pc_revoke_is_refused():
    with connected(ENV_TOKEN, "pc-umar") as websocket:
        websocket.receive_json()
        main_id = client.get("/devices", headers=OWNER_HEADERS).json()[0]["id"]

        response = client.post(f"/devices/{main_id}/revoke", headers=OWNER_HEADERS)

        # Still connected: the Node can keep talking.
        assert client.get("/devices", headers=OWNER_HEADERS).json()[0]["connected"] is True
    assert response.status_code == status.HTTP_409_CONFLICT


def test_revoke_drops_the_live_node_and_blocks_reconnect():
    created = add_device()
    with connected(created["token"], "laptop-1") as websocket:
        websocket.receive_json()

        response = client.post(f"/devices/{created['id']}/revoke", headers=OWNER_HEADERS)

        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["revoked_at"] is not None
    assert error.value.code == status.WS_1008_POLICY_VIOLATION

    with pytest.raises(WebSocketDisconnect) as error:
        with connected(created["token"], "laptop-1"):
            pass
    assert error.value.code == status.WS_1008_POLICY_VIOLATION


def test_revoked_token_is_refused_on_voice_routes():
    created = add_device()
    client.post(f"/devices/{created['id']}/revoke", headers=OWNER_HEADERS)

    response = client.get(
        "/voice/state", headers={"Authorization": f"Bearer {created['token']}"}
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_node_token_cannot_chat_as_another_device():
    token = add_device()["token"]
    with connected(token, "laptop-1") as websocket:
        websocket.receive_json()

    response = client.post(
        "/nodes/pc-umar/chat",
        json={"message": "open spotify"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_devices_are_owner_only():
    response = client.get("/devices", headers={"Authorization": f"Bearer {ENV_TOKEN}"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_blank_name_is_rejected():
    response = client.post("/devices", json={"name": "  "}, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_revoke_unknown_device_is_404():
    response = client.post(
        "/devices/00000000-0000-0000-0000-000000000000/revoke", headers=OWNER_HEADERS
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_revoked_device_can_be_deleted():
    created = add_device()
    client.post(f"/devices/{created['id']}/revoke", headers=OWNER_HEADERS)

    response = client.delete(f"/devices/{created['id']}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert client.get("/devices", headers=OWNER_HEADERS).json() == []


def test_active_device_must_be_revoked_before_delete():
    created = add_device()

    response = client.delete(f"/devices/{created['id']}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert len(client.get("/devices", headers=OWNER_HEADERS).json()) == 1
