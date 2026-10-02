from contextlib import contextmanager

import pytest
from uuid import UUID, uuid4
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
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.chat.dependencies import get_chat_provider
from features.chat.provider import BrainReply
from features.chat.schemas import ChatTurn
from features.commands.dependencies import get_command_record_repository
from features.commands.models.command_record import CommandRecord
from features.commands.repository import CommandRecordRepository
from features.conversations.dependencies import get_conversation_repository
from features.conversations.repository import ConversationRepository
from features.memories.dependencies import get_memory_repository
from features.memories.repository import MemoryRepository
from features.personalities.dependencies import get_personality_repository
from features.personalities.repository import PersonalityRepository
from features.projects.dependencies import get_project_repository
from features.projects.repository import ProjectRepository
from features.nodes.connection_registry import (
    NodeConnectionRegistry,
    get_connection_registry,
)
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.models.site_shortcut import SiteShortcut
from features.shortcuts.repository import ShortcutRepository
from storage.base import Base

from venus_protocol.schemas.commands import (
    CommandResult,
    OpenApplicationCommand,
    OpenProjectCommand,
    OpenUrlCommand,
)

TEST_NODE_TOKEN = "test-node-token"
TEST_OWNER_TOKEN = "test-owner-token"
OPEN_SPOTIFY = {"application_id": "spotify"}
OPEN_YOUTUBE = {"url": "https://www.youtube.com"}
OPEN_VENUS = {"project_name": "Venus"}
# The Node reports the apps and project folders this PC can open; Core only accepts those
PC_UMAR_HELLO = {
    "device_id": "PC-Umar",
    "apps": [{"name": "Spotify", "app_id": "spotify"}],
    "projects": ["Venus"],
}


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
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}
        proposal = client.post(
            "/nodes/PC-Umar/commands", headers=owner_headers,
            json=OPEN_SPOTIFY,
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


@contextmanager
def connected_pc_umar():
    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}
        yield websocket


@pytest.fixture(autouse=True)
def command_records():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    auth_repository = AuthRepository(engine)
    app.dependency_overrides[get_auth_repository] = lambda: auth_repository
    settings_repository = SettingsRepository(engine)
    app.dependency_overrides[get_settings_repository] = (
        lambda: settings_repository
    )
    shortcut_repository = ShortcutRepository(engine)
    app.dependency_overrides[get_shortcut_repository] = (
        lambda: shortcut_repository
    )
    conversation_repository = ConversationRepository(engine)
    app.dependency_overrides[get_conversation_repository] = (
        lambda: conversation_repository
    )
    project_repository = ProjectRepository(engine)
    app.dependency_overrides[get_project_repository] = lambda: project_repository
    personality_repository = PersonalityRepository(engine)
    app.dependency_overrides[get_personality_repository] = (
        lambda: personality_repository
    )
    memory_repository = MemoryRepository(engine)
    app.dependency_overrides[get_memory_repository] = lambda: memory_repository
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
        old_connection.send_json(PC_UMAR_HELLO)

        assert old_connection.receive_json() == {"device_id": "PC-Umar"}

        with client.websocket_connect(
            "/nodes/connect",
            headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
        ) as new_connection:
            new_connection.send_json(PC_UMAR_HELLO)

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
        websocket.send_json(PC_UMAR_HELLO)

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
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        response = client.get(
            "/nodes/PC-Umar/connection",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "device_id": "PC-Umar",
            "connected": True,
        }

    response = client.get(
        "/nodes/PC-Umar/connection",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

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
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        response = client.post(
            "/nodes/PC-Umar/commands",
            json=OPEN_SPOTIFY,
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

def test_propose_command_creates_awaiting_approval_record(
    command_records: CommandRecordRepository,
):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands",
            json=OPEN_SPOTIFY,
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
    command = OpenApplicationCommand.model_validate(response.json())
    stored_record = command_records.get(command.command_id)

    assert stored_record is not None
    assert stored_record.device_id == "PC-Umar"
    assert stored_record.application_id == "spotify"
    assert stored_record.state == "awaiting_approval"


def test_full_mode_proposal_dispatches_without_approval(
    command_records: CommandRecordRepository,
):
    owner_headers = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}
    client.put("/settings/mode", json={"mode": "full"}, headers=owner_headers)

    with connected_pc_umar() as websocket:
        response = client.post(
            "/nodes/PC-Umar/commands", json=OPEN_SPOTIFY, headers=owner_headers,
        )
        # The Node gets the command with no approval call in between.
        assert websocket.receive_json() == response.json()

    command = OpenApplicationCommand.model_validate(response.json())
    stored_record = command_records.get(command.command_id)
    assert stored_record is not None
    assert stored_record.state == "dispatched"


def test_propose_url_creates_awaiting_approval_record(
    command_records: CommandRecordRepository,
):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/open-url",
            json=OPEN_YOUTUBE,
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
    command = OpenUrlCommand.model_validate(response.json())
    stored_record = command_records.get(command.command_id)

    assert stored_record is not None
    assert stored_record.kind == "open_url"
    assert stored_record.url == "https://www.youtube.com/"
    assert stored_record.application_id is None
    assert stored_record.state == "awaiting_approval"


def test_approving_url_proposal_sends_open_url_command():
    owner_headers = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

    with connected_pc_umar() as websocket:
        proposal = client.post(
            "/nodes/PC-Umar/commands/open-url",
            json=OPEN_YOUTUBE,
            headers=owner_headers,
        ).json()
        approval = client.post(
            f"/commands/{proposal['command_id']}/approval",
            json={"approved": True},
            headers=owner_headers,
        )
        # Approval rebuilds the command from the record; it must stay a URL command
        sent = OpenUrlCommand.model_validate(websocket.receive_json())

    assert approval.status_code == 200
    assert str(sent.url) == "https://www.youtube.com/"


def test_full_mode_url_proposal_dispatches_without_approval(
    command_records: CommandRecordRepository,
):
    owner_headers = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}
    client.put("/settings/mode", json={"mode": "full"}, headers=owner_headers)

    with connected_pc_umar() as websocket:
        response = client.post(
            "/nodes/PC-Umar/commands/open-url",
            json=OPEN_YOUTUBE,
            headers=owner_headers,
        )
        assert websocket.receive_json() == response.json()

    command = OpenUrlCommand.model_validate(response.json())
    stored_record = command_records.get(command.command_id)
    assert stored_record is not None
    assert stored_record.state == "dispatched"


def test_propose_url_rejects_file_scheme():
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/open-url",
            json={"url": "file:///C:/Windows/System32/cmd.exe"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_propose_url_rejects_disconnected_node():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = lambda: registry

    response = client.post(
        "/nodes/PC-Umar/commands/open-url",
        json=OPEN_YOUTUBE,
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Node is not connected"}


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
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        websocket.send_json(unsolicited_result.model_dump(mode="json"))

    assert result_registry.get(command_id) is None


def test_propose_command_rejects_disconnected_node():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = (
        lambda: registry
    )

    response = client.post(
        "/nodes/PC-Umar/commands",
        json=OPEN_SPOTIFY,
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Node is not connected"}


def test_owner_denial_completes_proposal_without_dispatch(
    command_records: CommandRecordRepository,
):
    with connected_pc_umar():
        proposal_response = client.post(
            "/nodes/PC-Umar/commands",
            json=OPEN_SPOTIFY,
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
    with connected_pc_umar():
        proposal_response = client.post(
            "/nodes/PC-Umar/commands",
            json=OPEN_SPOTIFY,
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
        "detail": "Not authenticated",
    }


def test_propose_command_rejects_blank_application():
    response = client.post(
        "/nodes/PC-Umar/commands",
        json={"application_id": "   "},
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_propose_command_rejects_app_not_on_node():
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands",
            json={"application_id": "notepad-id"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() == {"detail": "Application is not on this PC"}


def test_propose_command_rejects_missing_owner_token():
    response = client.post("/nodes/PC-Umar/commands", json=OPEN_SPOTIFY)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Not authenticated",
    }


def test_propose_command_rejects_invalid_owner_token():
    response = client.post(
        "/nodes/PC-Umar/commands",
        json=OPEN_SPOTIFY,
        headers={"Authorization": "Bearer invalid-owner-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Not authenticated",
    }


def test_proposed_commands_share_connected_node_session():
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
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        first_response = client.post(
            "/nodes/PC-Umar/commands",
            json=OPEN_SPOTIFY,
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
            "/nodes/PC-Umar/commands",
            json=OPEN_SPOTIFY,
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
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        response = client.post(
            "/nodes/PC-Umar/commands",
            json=OPEN_SPOTIFY,
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
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        proposal_response = client.post(
            "/nodes/PC-Umar/commands",
            json=OPEN_SPOTIFY,
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
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        proposal_response = client.post(
            "/nodes/PC-Umar/commands",
            json=OPEN_SPOTIFY,
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
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}
        proposal = client.post(
            "/nodes/PC-Umar/commands", headers=owner_headers,
            json=OPEN_SPOTIFY,
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


def test_connection_status_rejects_missing_owner_token():
    response = client.get("/nodes/PC-Umar/connection")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_list_nodes_rejects_missing_owner_token():
    response = client.get("/nodes")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_list_nodes_shows_connected_node():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = (
        lambda: registry
    )

    with client.websocket_connect(
        "/nodes/connect",
        headers={"Authorization": f"Bearer {TEST_NODE_TOKEN}"},
    ) as websocket:
        websocket.send_json(PC_UMAR_HELLO)
        assert websocket.receive_json() == {"device_id": "PC-Umar"}

        response = client.get(
            "/nodes",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"device_ids": ["PC-Umar"]}


def test_list_nodes_empty_when_none_connected():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = (
        lambda: registry
    )

    response = client.get(
        "/nodes",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"device_ids": []}


def test_list_node_apps_returns_reported_apps():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = (
        lambda: registry
    )

    with connected_pc_umar():
        response = client.get(
            "/nodes/PC-Umar/apps",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "device_id": "PC-Umar",
        "apps": [{"name": "Spotify", "app_id": "spotify"}],
    }


def test_list_node_apps_rejects_disconnected_node():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = (
        lambda: registry
    )

    response = client.get(
        "/nodes/PC-Umar/apps",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Node is not connected"}


def test_list_node_apps_rejects_missing_owner_token():
    response = client.get("/nodes/PC-Umar/apps")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {"detail": "Not authenticated"}


def test_list_node_projects_returns_reported_projects():
    with connected_pc_umar():
        response = client.get(
            "/nodes/PC-Umar/projects",
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"device_id": "PC-Umar", "projects": ["Venus"]}


def test_list_node_projects_rejects_disconnected_node():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = lambda: registry

    response = client.get(
        "/nodes/PC-Umar/projects",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Node is not connected"}


def test_propose_project_creates_awaiting_approval_record(
    command_records: CommandRecordRepository,
):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/open-project",
            json=OPEN_VENUS,
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )
    command = OpenProjectCommand.model_validate(response.json())
    stored_record = command_records.get(command.command_id)

    assert stored_record is not None
    assert stored_record.kind == "open_project"
    assert stored_record.project_name == "Venus"
    assert stored_record.application_id is None
    assert stored_record.state == "awaiting_approval"


def test_approving_project_proposal_sends_open_project_command():
    owner_headers = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

    with connected_pc_umar() as websocket:
        proposal = client.post(
            "/nodes/PC-Umar/commands/open-project",
            json=OPEN_VENUS,
            headers=owner_headers,
        ).json()
        approval = client.post(
            f"/commands/{proposal['command_id']}/approval",
            json={"approved": True},
            headers=owner_headers,
        )
        # Approval rebuilds the command from the record; it must stay a project command
        sent = OpenProjectCommand.model_validate(websocket.receive_json())

    assert approval.status_code == 200
    assert sent.project_name == "Venus"


def test_full_mode_project_proposal_dispatches_without_approval(
    command_records: CommandRecordRepository,
):
    owner_headers = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}
    client.put("/settings/mode", json={"mode": "full"}, headers=owner_headers)

    with connected_pc_umar() as websocket:
        response = client.post(
            "/nodes/PC-Umar/commands/open-project",
            json=OPEN_VENUS,
            headers=owner_headers,
        )
        assert websocket.receive_json() == response.json()

    command = OpenProjectCommand.model_validate(response.json())
    stored_record = command_records.get(command.command_id)
    assert stored_record is not None
    assert stored_record.state == "dispatched"


def test_propose_project_rejects_unreported_project():
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/open-project",
            json={"project_name": "fastapi_blog"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() == {"detail": "Project is not on this PC"}


def test_propose_project_rejects_path_like_name():
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/open-project",
            json={"project_name": ".."},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_propose_project_rejects_disconnected_node():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = lambda: registry

    response = client.post(
        "/nodes/PC-Umar/commands/open-project",
        json=OPEN_VENUS,
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Node is not connected"}


def test_text_command_proposes_app_with_label(
    command_records: CommandRecordRepository,
):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/text",
            json={"text": "open spot"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()
    command = OpenApplicationCommand.model_validate(
        {key: value for key, value in body.items() if key != "label"},
    )
    stored_record = command_records.get(command.command_id)

    assert response.status_code == 200
    assert body["label"] == "Spotify"
    assert command.application_id == "spotify"
    assert stored_record is not None
    assert stored_record.state == "awaiting_approval"


def test_text_command_search_is_saved_as_url_command(
    command_records: CommandRecordRepository,
):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/text",
            json={"text": "youtube teo"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()
    stored_record = command_records.get(UUID(body["command_id"]))

    assert body["label"] == "YouTube search: teo"
    assert stored_record is not None
    assert stored_record.kind == "open_url"
    assert stored_record.url == "https://www.youtube.com/results?search_query=teo"


def test_full_mode_text_command_dispatches_without_approval(
    command_records: CommandRecordRepository,
):
    owner_headers = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}
    client.put("/settings/mode", json={"mode": "full"}, headers=owner_headers)

    with connected_pc_umar() as websocket:
        response = client.post(
            "/nodes/PC-Umar/commands/text",
            json={"text": "open my project venus"},
            headers=owner_headers,
        )
        sent = OpenProjectCommand.model_validate(websocket.receive_json())

    stored_record = command_records.get(sent.command_id)

    assert response.json()["label"] == "Venus in VS Code"
    assert sent.project_name == "Venus"
    assert stored_record is not None
    assert stored_record.state == "dispatched"


def test_chat_runs_a_command_the_parser_understands(
    command_records: CommandRecordRepository,
):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "open spot"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()
    stored_record = command_records.get(UUID(body["command_id"]))

    assert response.status_code == 200
    assert body["type"] == "command"
    assert body["label"] == "Spotify"
    assert stored_record is not None
    assert stored_record.state == "awaiting_approval"


def test_chat_sends_unknown_app_to_the_brain(
    command_records: CommandRecordRepository,
):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "open zzz"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "reply"
    assert body["reply"] == "Fake Venus: open zzz"


def test_chat_open_with_extra_words_goes_to_the_brain(
    command_records: CommandRecordRepository,
):
    app.dependency_overrides[get_chat_provider] = lambda: ToolBrain("open Spotify")

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "open spotify for me love"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "command"
    assert body["label"] == "Spotify"


def test_chat_asks_the_brain_when_the_parser_does_not_understand():
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "hello"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "reply"
    assert body["reply"] == "Fake Venus: hello"


class ToolBrain:
    """A brain that always picks a tool, already written as parser text."""

    def __init__(self, command: str) -> None:
        self.command = command

    async def reply(
        self, message: str, history: list[ChatTurn], instructions: str,
    ) -> BrainReply:
        return BrainReply(command=self.command)


def test_chat_brain_tool_choice_proposes_command(
    command_records: CommandRecordRepository,
):
    app.dependency_overrides[get_chat_provider] = lambda: ToolBrain("open spotify")

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "can you open spotify for me"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()
    stored_record = command_records.get(UUID(body["command_id"]))

    assert response.status_code == 200
    assert body["type"] == "command"
    assert body["label"] == "Spotify"
    assert stored_record is not None
    assert stored_record.state == "awaiting_approval"


def test_chat_brain_tool_choice_still_goes_through_parser_checks():
    # Luna can't open anything the owner couldn't type themselves.
    app.dependency_overrides[get_chat_provider] = lambda: ToolBrain("open zzz")

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "can you open zzz for me"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()

    assert response.status_code == 200
    assert body["type"] == "reply"
    assert body["reply"] == "No app called zzz on this PC"


@pytest.fixture
def conversations(command_records: CommandRecordRepository) -> ConversationRepository:
    return app.dependency_overrides[get_conversation_repository]()


class RecordingBrain:
    """A brain that answers with words and remembers what it was given."""

    def __init__(self) -> None:
        self.history: list[ChatTurn] | None = None
        self.instructions: str | None = None

    async def reply(
        self, message: str, history: list[ChatTurn], instructions: str,
    ) -> BrainReply:
        self.history = history
        self.instructions = instructions
        return BrainReply(text="Your name is Umar.")


def test_chat_starts_a_conversation_and_saves_both_lines(
    conversations: ConversationRepository,
):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "hello"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    conversation_id = UUID(response.json()["conversation_id"])
    saved = conversations.messages(conversation_id)

    assert conversations.get(conversation_id).title == "hello"
    assert [(m.role, m.content) for m in saved] == [
        ("user", "hello"),
        ("assistant", "Fake Venus: hello"),
    ]


def test_chat_sends_saved_turns_to_the_brain(conversations: ConversationRepository):
    conversation_id = conversations.create("my name is umar")
    conversations.add_exchange(conversation_id, "my name is umar", "Nice to meet you.")
    brain = RecordingBrain()
    app.dependency_overrides[get_chat_provider] = lambda: brain

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "whats my name", "conversation_id": str(conversation_id)},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.json()["conversation_id"] == str(conversation_id)
    assert brain.history == [
        ChatTurn(role="user", content="my name is umar"),
        ChatTurn(role="assistant", content="Nice to meet you."),
    ]
    assert len(conversations.messages(conversation_id)) == 4


def test_chat_saves_command_proposal_as_text(conversations: ConversationRepository):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "open spot"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    conversation_id = UUID(response.json()["conversation_id"])
    saved = conversations.messages(conversation_id)

    assert saved[-1].content == "Proposed: Spotify"


def test_chat_rejects_unknown_conversation(conversations: ConversationRepository):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "hello", "conversation_id": str(uuid4())},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert conversations.list_all() == []


def test_chat_starts_new_conversation_inside_project(
    conversations: ConversationRepository,
):
    project = app.dependency_overrides[get_project_repository]().create("Java")

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "explain loops", "project_id": str(project.id)},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    conversation_id = UUID(response.json()["conversation_id"])
    assert conversations.get(conversation_id).project_id == project.id


def test_chat_rejects_unknown_project(conversations: ConversationRepository):
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "hello", "project_id": str(uuid4())},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Project not found"
    assert conversations.list_all() == []


def test_new_chat_in_archived_project_is_rejected(
    conversations: ConversationRepository,
):
    projects = app.dependency_overrides[get_project_repository]()
    project = projects.create("Old")
    projects.set_archived(project.id, True)

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "hello", "project_id": str(project.id)},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["detail"] == "Project is archived"
    assert conversations.list_all() == []


def test_chat_sends_active_personality_to_the_brain(
    conversations: ConversationRepository,
):
    personalities = app.dependency_overrides[get_personality_repository]()
    personal = personalities.create("Personal", "Be flirty.")
    personalities.create("Professional", "Be polite.")
    personalities.activate(personal.id)
    brain = RecordingBrain()
    app.dependency_overrides[get_chat_provider] = lambda: brain

    with connected_pc_umar():
        client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "hello"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert "Be flirty." in brain.instructions
    assert "Be polite." not in brain.instructions
    # Built-in sites are always listed, so Luna uses them instead of guessing.
    assert "youtube" in brain.instructions


def test_chat_moved_into_project_uses_its_instructions(
    conversations: ConversationRepository,
):
    projects = app.dependency_overrides[get_project_repository]()
    project = projects.create("Java")
    projects.set_instructions(project.id, "Explain step by step.")
    # Started outside the project, then moved in.
    conversation_id = conversations.create("loops")
    conversations.set_project(conversation_id, project.id)
    brain = RecordingBrain()
    app.dependency_overrides[get_chat_provider] = lambda: brain

    with connected_pc_umar():
        client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "what is a loop", "conversation_id": str(conversation_id)},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert brain.instructions.endswith("Explain step by step.")


class MemoryBrain:
    """A brain that always chooses to remember a fact."""

    async def reply(
        self, message: str, history: list[ChatTurn], instructions: str,
    ) -> BrainReply:
        return BrainReply(text="Lo-fi is perfect for coding!", memory="Owner likes lo-fi")


def test_chat_remember_saves_fact_without_a_command(
    conversations: ConversationRepository,
):
    memories = app.dependency_overrides[get_memory_repository]()
    # The rule answers, so the brain is never asked.
    app.dependency_overrides[get_chat_provider] = lambda: ToolBrain("open spotify")

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "remember I like lo-fi"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()

    assert body["type"] == "reply"
    assert body["reply"] == "Saved: I like lo-fi"
    assert [memory.text for memory in memories.list_all()] == ["I like lo-fi"]


def test_chat_brain_save_memory_saves_fact(conversations: ConversationRepository):
    memories = app.dependency_overrides[get_memory_repository]()
    app.dependency_overrides[get_chat_provider] = lambda: MemoryBrain()

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "i really love lo-fi music"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.json()["reply"] == (
        "Lo-fi is perfect for coding!\n\nSaved to memory: Owner likes lo-fi"
    )
    assert [memory.text for memory in memories.list_all()] == ["Owner likes lo-fi"]


def test_chat_sends_saved_facts_to_the_brain(conversations: ConversationRepository):
    memories = app.dependency_overrides[get_memory_repository]()
    memories.create("Owner name is Umar")
    brain = RecordingBrain()
    app.dependency_overrides[get_chat_provider] = lambda: brain

    with connected_pc_umar():
        client.post(
            "/nodes/PC-Umar/chat",
            json={"message": "hello"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert "What you know about the owner: Owner name is Umar." in brain.instructions


def test_chat_requires_owner():
    response = client.post("/nodes/PC-Umar/chat", json={"message": "hello"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_text_command_rejects_text_venus_does_not_understand():
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/text",
            json={"text": "make me a sandwich"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() == {"detail": "Venus didn't understand that"}


def test_text_command_rejects_invalid_link():
    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/text",
            json={"text": "a.b:99999"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert response.json() == {"detail": "That link doesn't look right"}


def test_text_command_rejects_disconnected_node():
    registry = NodeConnectionRegistry()
    app.dependency_overrides[get_connection_registry] = lambda: registry

    response = client.post(
        "/nodes/PC-Umar/commands/text",
        json={"text": "open spotify"},
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": "Node is not connected"}


def test_text_command_uses_owner_shortcut(
    command_records: CommandRecordRepository,
):
    shortcuts = app.dependency_overrides[get_shortcut_repository]()
    shortcuts.add(SiteShortcut(
        keyword="comix",
        label="Comix",
        home_url="https://comix.to/",
        search_url="https://comix.to/search?q={words}",
    ))

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/text",
            json={"text": "comix solo leveling"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    body = response.json()
    stored_record = command_records.get(UUID(body["command_id"]))

    assert body["label"] == "Comix search: solo leveling"
    assert stored_record is not None
    assert stored_record.url == "https://comix.to/search?q=solo+leveling"


def test_owner_shortcut_replaces_built_in_site(
    command_records: CommandRecordRepository,
):
    shortcuts = app.dependency_overrides[get_shortcut_repository]()
    shortcuts.add(SiteShortcut(
        keyword="youtube",
        label="YouTube Music",
        home_url="https://music.youtube.com/",
        search_url="https://music.youtube.com/search?q={words}",
    ))

    with connected_pc_umar():
        response = client.post(
            "/nodes/PC-Umar/commands/text",
            json={"text": "youtube lofi"},
            headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
        )

    stored_record = command_records.get(UUID(response.json()["command_id"]))

    assert stored_record is not None
    assert stored_record.url == "https://music.youtube.com/search?q=lofi"
