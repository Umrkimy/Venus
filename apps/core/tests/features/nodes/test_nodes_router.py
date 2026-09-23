import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
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


def test_result_storage_failure_does_not_publish_success(
    command_records: CommandRecordRepository, monkeypatch,
):
    results = CommandResultRegistry()
    connections = NodeConnectionRegistry()
    app.dependency_overrides[get_command_result_registry] = lambda: results
    app.dependency_overrides[get_connection_registry] = lambda: connections

    def fail_completion(*args, **kwargs):
        raise SQLAlchemyError("Injected database failure")

    monkeypatch.setattr(command_records, "complete", fail_completion)
    owner_headers = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "PC-Umar"})
        assert websocket.receive_json() == {"device_id": "PC-Umar"}
        proposal = client.post(
            "/nodes/PC-Umar/commands/fake", headers=owner_headers,
        ).json()
        command = OpenApplicationCommand.model_validate(proposal)
        approval = client.post(
            f"/commands/{command.command_id}/approval",
            json={"approved": True}, headers=owner_headers,
        )
        assert approval.status_code == 200
        assert websocket.receive_json() == proposal
        websocket.send_json({
            "command_id": str(command.command_id), "status": "succeeded",
        })
        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()
        assert error.value.code == status.WS_1011_INTERNAL_ERROR

    assert results.get(command.command_id) is None
    stored = command_records.get(command.command_id)
    assert stored is not None
    assert stored.state == "dispatched"
    assert stored.completed_at is None
    response = client.get(
        f"/commands/{command.command_id}/result", headers=owner_headers,
    )
    assert response.status_code == 404
    assert connections.get("PC-Umar") is None


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



def test_node_connection_records_command_result(command_records: CommandRecordRepository):
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
        approval = client.post(
            f"/commands/{command.command_id}/approval",
            json={"approved": True},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
        assert approval.status_code == 200
        assert websocket.receive_json() == approval.json()
        assert command_records.get(command.command_id).state == "dispatched"
        result = CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="Fake command completed",
        )

        websocket.send_json(result.model_dump(mode="json"))

    assert result_registry.get(command.command_id) == result

    stored_record = command_records.get(command.command_id)

    assert stored_record is not None
    assert stored_record.state == "succeeded"
    assert stored_record.detail == "Fake command completed"
    assert stored_record.completed_at is not None

def test_fake_command_creates_awaiting_approval_record(
    command_records: CommandRecordRepository,
):
    response = client.post(
        "/nodes/PC-Umar/commands/fake",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )
    command = OpenApplicationCommand.model_validate(response.json())
    stored_record = command_records.get(command.command_id)

    assert stored_record is not None
    assert stored_record.device_id == "PC-Umar"
    assert stored_record.application_id == "spotify"
    assert stored_record.state == "awaiting_approval"


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


def test_fake_command_creates_proposal_for_disconnected_node():
    response = client.post(
        "/nodes/PC-Umar/commands/fake",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_200_OK


def test_owner_denial_completes_proposal_without_dispatch(
    command_records: CommandRecordRepository,
):
    proposal_response = client.post(
        "/nodes/PC-Umar/commands/fake",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )
    command = OpenApplicationCommand.model_validate(proposal_response.json())

    denial_response = client.post(
        f"/commands/{command.command_id}/approval",
        json={"approved": False},
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert denial_response.status_code == status.HTTP_200_OK
    assert denial_response.json() == {
        "command_id": str(command.command_id),
        "status": "denied",
    }

    stored_record = command_records.get(command.command_id)

    assert stored_record is not None
    assert stored_record.state == "denied"
    assert stored_record.detail == "Owner denied command"
    assert stored_record.completed_at is not None


def test_approval_rejects_disconnected_node_without_dispatch(
    command_records: CommandRecordRepository,
):
    proposal_response = client.post(
        "/nodes/PC-Umar/commands/fake",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )
    command = OpenApplicationCommand.model_validate(proposal_response.json())

    approval_response = client.post(
        f"/commands/{command.command_id}/approval",
        json={"approved": True},
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert approval_response.status_code == status.HTTP_409_CONFLICT
    assert approval_response.json() == {"detail": "Node is not connected"}
    assert command_records.get(command.command_id).state == "awaiting_approval"


def test_approval_rejects_missing_owner_token():
    response = client.post(
        f"/commands/{uuid4()}/approval",
        json={"approved": True},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid development owner token",
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
        first_approval = client.post(
            f"/commands/{first_command.command_id}/approval",
            json={"approved": True},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
        assert first_approval.status_code == 200
        assert websocket.receive_json() == first_approval.json()

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
        second_approval = client.post(
            f"/commands/{second_command.command_id}/approval",
            json={"approved": True},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
        assert second_approval.status_code == 200
        assert websocket.receive_json() == second_approval.json()

        second_result = CommandResult(
            command_id=second_command.command_id,
            status="succeeded",
            detail="Second fake command completed",
        )
        websocket.send_json(second_result.model_dump(mode="json"))

    assert result_registry.get(first_command.command_id) == first_result
    assert result_registry.get(second_command.command_id) == second_result


def test_node_connection_rejects_wrong_result_without_completing_record(
    command_records: CommandRecordRepository,
):
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
        approval = client.post(
            f"/commands/{command.command_id}/approval",
            json={"approved": True},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
        assert approval.status_code == 200
        assert websocket.receive_json() == approval.json()

        wrong_result = CommandResult(
            # Use a valid but unissued ID to exercise Core's ownership check.
            command_id=uuid4(),
            status="succeeded",
            detail="Node reported a result for a different command",
        )
        websocket.send_json(wrong_result.model_dump(mode="json"))

        with pytest.raises(WebSocketDisconnect) as error:
            websocket.receive_json()

    assert error.value.code == status.WS_1008_POLICY_VIOLATION
    assert result_registry.get(wrong_result.command_id) is None

    stored_record = command_records.get(command.command_id)

    assert stored_record is not None
    assert stored_record.state == "dispatched"
    assert stored_record.detail is None
    assert stored_record.completed_at is None


def test_approval_rejects_repeated_decision():
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

        proposal_response = client.post(
            "/nodes/PC-Umar/commands/fake",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
        command = OpenApplicationCommand.model_validate(
            proposal_response.json(),
        )

        first_approval = client.post(
            f"/commands/{command.command_id}/approval",
            json={"approved": True},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

        assert first_approval.status_code == status.HTTP_200_OK
        assert websocket.receive_json() == first_approval.json()

        second_approval = client.post(
            f"/commands/{command.command_id}/approval",
            json={"approved": True},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

        assert second_approval.status_code == status.HTTP_409_CONFLICT
        assert second_approval.json() == {
            "detail": "Command is not awaiting approval",
        }


def test_approval_rejects_approval_after_denial(
    command_records: CommandRecordRepository,
):
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

        proposal_response = client.post(
            "/nodes/PC-Umar/commands/fake",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
        command = OpenApplicationCommand.model_validate(
            proposal_response.json(),
        )

        first_approval = client.post(
            f"/commands/{command.command_id}/approval",
            json={"approved": False},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

        assert first_approval.status_code == status.HTTP_200_OK

        second_approval = client.post(
            f"/commands/{command.command_id}/approval",
            json={"approved": True},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

        assert second_approval.status_code == status.HTTP_409_CONFLICT
        assert second_approval.json() == {
            "detail": "Command is not awaiting approval",
        }
        stored_record = command_records.get(command.command_id)
        assert stored_record is not None
        assert stored_record.state == "denied"


def test_approval_rejects_unknown_command():
    unknown_command_id = uuid4()

    response = client.post(
        f"/commands/{unknown_command_id}/approval",
        json={"approved": True},
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Command not found"}


def test_approval_rejects_expired_proposal(
    command_records: CommandRecordRepository,
):
    command_id = uuid4()
    command_records.create(
        CommandRecord(
            command_id=command_id,
            device_id="PC-Umar",
            application_id="spotify",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
    )

    response = client.post(
        f"/commands/{command_id}/approval",
        json={"approved": True},
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Command has expired"}

    stored_record = command_records.get(command_id)
    assert stored_record is not None
    assert stored_record.state == "awaiting_approval"


@pytest.mark.parametrize("approved", [True, False])
def test_approval_rejects_expiry_between_read_and_decision(
    command_records: CommandRecordRepository, monkeypatch, approved: bool,
):
    connections = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = lambda: connections
    decide = command_records.decide_approval

    def decide_at_expiry(command_id, *, approved, decided_at):
        stored = command_records.get(command_id)
        assert stored is not None
        return decide(
            command_id, approved=approved,
            decided_at=stored.expires_at.replace(tzinfo=timezone.utc),
        )

    monkeypatch.setattr(command_records, "decide_approval", decide_at_expiry)
    owner_headers = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json({"device_id": "PC-Umar"})
        assert websocket.receive_json() == {"device_id": "PC-Umar"}
        proposal = client.post(
            "/nodes/PC-Umar/commands/fake", headers=owner_headers,
        ).json()
        command = OpenApplicationCommand.model_validate(proposal)
        response = client.post(
            f"/commands/{command.command_id}/approval",
            json={"approved": approved}, headers=owner_headers,
        )
        assert response.status_code == 409
        assert response.json() == {"detail": "Command has expired"}
    stored = command_records.get(command.command_id)
    assert stored is not None
    assert stored.state == "awaiting_approval"


def test_approval_rejects_string_decision(
    command_records: CommandRecordRepository
):
    command_id = uuid4()
    command_records.create(
        CommandRecord(
            command_id=command_id,
            device_id="PC-Umar",
            application_id="spotify",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
    )

    response = client.post(
        f"/commands/{command_id}/approval",
        json={"approved": "no"},
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    stored_record = command_records.get(command_id)
    assert stored_record is not None
    assert stored_record.state == "awaiting_approval"
