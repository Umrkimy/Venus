import pytest
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from starlette.websockets import WebSocketDisconnect

from config import CoreSettings, get_settings
from main import app

from features.commands.result_registry import (
    CommandResultRegistry,
    get_command_result_registry,
)
from features.commands.dependencies import get_command_record_repository
from features.commands.models.command_record import CommandRecord
from features.commands.repository import CommandRecordRepository
from features.nodes.connection_registry import (
    NodeConnectionRegistry,
    get_connection_registry,
)
from storage.base import Base

from venus_protocol.schemas.commands import (
    CommandResult,
    OpenApplicationCommand,
)

TEST_NODE_TOKEN = "test-node-token"
TEST_OWNER_TOKEN = "test-owner-token"


client = TestClient(app)


@pytest.fixture(autouse=True)
def command_records():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield CommandRecordRepository(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def override_node_settings(command_records: CommandRecordRepository):
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token=TEST_NODE_TOKEN,
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    app.dependency_overrides[get_command_record_repository] = (
        lambda: command_records
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


def test_node_connection_rejects_binary_hello():
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_bytes(b"not-a-hello")

        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()

    assert error.value.code == status.WS_1008_POLICY_VIOLATION


def test_node_connection_handles_disconnect_before_hello():
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ):
        pass


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

    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "PC-Umar"})
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        response = client.post(
            "/nodes/PC-Umar/commands/fake",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
        command = OpenApplicationCommand.model_validate(response.json())
        assert websocket.receive_json() == response.json()
        result = CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="Fake command completed",
        )

        websocket.send_json(result.model_dump(mode="json"))

    assert result_registry.get(command.command_id) == result


def test_fake_command_is_saved_before_dispatch(
    command_records: CommandRecordRepository,
):
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "PC-Umar"})
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        response = client.post(
            "/nodes/PC-Umar/commands/fake",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
        command = OpenApplicationCommand.model_validate(response.json())
        stored_record = command_records.get(command.command_id)

        assert stored_record is not None
        assert stored_record.device_id == "PC-Umar"
        assert stored_record.application_id == "spotify"
        assert stored_record.state == "pending"
        assert websocket.receive_json() == response.json()


def test_node_connection_rejects_unsolicited_result():
    connection_registry = NodeConnectionRegistry()
    result_registry = CommandResultRegistry()
    app.dependency_overrides[get_connection_registry] = (
        lambda: connection_registry
    )
    app.dependency_overrides[get_command_result_registry] = (
        lambda: result_registry
    )
    command_id = uuid4()
    unsolicited_result = CommandResult(
        command_id=command_id,
        status="succeeded",
        detail="Node claimed success without a Core command",
    )

    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "PC-Umar"})
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        websocket.send_json(unsolicited_result.model_dump(mode="json"))

    assert result_registry.get(command_id) is None


def test_fake_command_rejects_disconnected_node():
    response = client.post(
        "/nodes/PC-Umar/commands/fake",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {
        "detail": "Node is not connected",
    }


def test_fake_command_rejects_missing_owner_token():
    response = client.post("/nodes/PC-Umar/commands/fake")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid development owner token",
    }


def test_fake_command_rejects_invalid_owner_token():
    response = client.post(
        "/nodes/PC-Umar/commands/fake",
        headers={"Authorization": "Bearer invalid-owner-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid development owner token",
    }


def test_fake_commands_share_connected_node_session():
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

        first_response = client.post(
            "/nodes/PC-Umar/commands/fake",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

        assert first_response.status_code == 200

        first_command = OpenApplicationCommand.model_validate(
            first_response.json(),
        )

        assert first_command.device_id == "PC-Umar"
        assert first_command.application_id == "spotify"
        assert websocket.receive_json() == first_response.json()

        first_result = CommandResult(
            command_id=first_command.command_id,
            status="succeeded",
            detail="Fake command completed",
        )
        websocket.send_json(first_result.model_dump(mode="json"))

        second_response = client.post(
            "/nodes/PC-Umar/commands/fake",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

        assert second_response.status_code == 200

        second_command = OpenApplicationCommand.model_validate(
            second_response.json(),
        )

        assert second_command.device_id == "PC-Umar"
        assert second_command.application_id == "spotify"
        assert websocket.receive_json() == second_response.json()

        second_result = CommandResult(
            command_id=second_command.command_id,
            status="succeeded",
            detail="Second fake command completed",
        )
        websocket.send_json(second_result.model_dump(mode="json"))

    assert result_registry.get(first_command.command_id) == first_result
    assert result_registry.get(second_command.command_id) == second_result
