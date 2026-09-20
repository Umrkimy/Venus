import pytest
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from config import CoreSettings, get_settings
from main import app

from command_result_registry import (
    CommandResultRegistry,
    get_command_result_registry,
)
from connection_registry import (
    NodeConnectionRegistry,
    get_connection_registry,
)

from venus_protocol.schemas.commands import (
    CommandResult,
    OpenApplicationCommand,
)

TEST_NODE_TOKEN = "test-node-token"


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_node_settings():
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token=TEST_NODE_TOKEN,
    )
    yield
    app.dependency_overrides.clear()


def test_node_connection_rejects_missing_token():
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect("/nodes/connect"):
            pass

    assert error.value.code == status.WS_1008_POLICY_VIOLATION


def test_node_connection_rejects_invalid_token():
    with pytest.raises(WebSocketDisconnect) as error:
        with client.websocket_connect(
            "/nodes/connect",
            headers={"Authorization": "Bearer invalid-token"},
        ):
            pass

    assert error.value.code == status.WS_1008_POLICY_VIOLATION


def test_node_connection_accepts_valid_hello():
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "laptop-1"})

        assert websocket.receive_json() == {"device_id": "laptop-1"}


def test_node_connection_rejects_invalid_hello():
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "   "})

        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()

    assert error.value.code == status.WS_1008_POLICY_VIOLATION


def test_node_connection_rejects_malformed_hello_json():
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_text("{not-valid-json}")

        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()

    assert error.value.code == status.WS_1008_POLICY_VIOLATION


def test_node_connection_rejects_message_after_hello():
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "laptop-1"})

        assert websocket.receive_json() == {"device_id": "laptop-1"}

        websocket.send_json({"command": "open spotify"})

        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()

    assert error.value.code == status.WS_1008_POLICY_VIOLATION


def test_node_connection_rejects_binary_message_after_hello():
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "laptop-1"})

        assert websocket.receive_json() == {"device_id": "laptop-1"}

        websocket.send_bytes(b"not-a-command")

        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()

    assert error.value.code == status.WS_1008_POLICY_VIOLATION


def test_node_connection_replaces_existing_device_connection():
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as old_connection:
        old_connection.send_json({"device_id": "PC-Umar"})

        assert old_connection.receive_json() == {"device_id": "PC-Umar"}

        with client.websocket_connect(
            "/nodes/connect",
            headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
        ) as new_connection:
            new_connection.send_json({"device_id": "PC-Umar"})

            assert new_connection.receive_json() == {
                "device_id": "PC-Umar",
            }

            with pytest.raises(WebSocketDisconnect) as error:
                old_connection.receive_json()

    assert error.value.code == status.WS_1000_NORMAL_CLOSURE


def test_node_connection_unregisters_disconnected_device():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = (
        lambda: registry
    )

    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "PC-Umar"})

        assert websocket.receive_json() == {"device_id": "PC-Umar"}

    assert registry.get("PC-Umar") is None


def test_node_connection_status_tracks_connection_lifecycle():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = (
        lambda: registry
    )

    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "PC-Umar"})
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        response = client.get("/nodes/PC-Umar/connection")

        assert response.status_code == 200
        assert response.json() == {
            "device_id": "PC-Umar",
            "connected": True,
        }

    response = client.get("/nodes/PC-Umar/connection")

    assert response.json() == {
        "device_id": "PC-Umar",
        "connected": False,
    }


def test_node_connection_records_command_result():
    result_registry = CommandResultRegistry()
    app.dependency_overrides[get_command_result_registry] = (
        lambda: result_registry
    )
    command_id = uuid4()
    result = CommandResult(
        command_id=command_id,
        status="succeeded",
        detail="Fake command completed",
    )

    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "PC-Umar"})
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        websocket.send_json(result.model_dump(mode="json"))

    assert result_registry.get(command_id) == result


def test_fake_command_rejects_disconnected_node():
    response = client.post("/nodes/PC-Umar/commands/fake")

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "detail": "Node is not connected",
    }


def test_fake_command_sends_to_connected_node():
    connection_registry = NodeConnectionRegistry()
    result_registry = CommandResultRegistry()
    app.dependency_overrides[get_connection_registry] = (
        lambda: connection_registry
    )
    app.dependency_overrides[get_command_result_registry] = (
        lambda: result_registry
    )

    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "PC-Umar"})
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        response = client.post("/nodes/PC-Umar/commands/fake")

        assert response.status_code == 200

        command = OpenApplicationCommand.model_validate(
            response.json(),
        )

        assert command.device_id == "PC-Umar"
        assert command.application_id == "spotify"
        assert websocket.receive_json() == response.json()

        result = CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="Fake command completed",
        )
        websocket.send_json(result.model_dump(mode="json"))

    assert result_registry.get(command.command_id) == result