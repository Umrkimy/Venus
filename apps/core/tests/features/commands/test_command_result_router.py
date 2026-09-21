from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone

from venus_protocol.schemas.commands import (
    CommandResult,
    OpenApplicationCommand,
)
from config import CoreSettings, get_settings
from features.commands.result_registry import (
    CommandResultRegistry,
    get_command_result_registry,
)
from main import app


TEST_OWNER_TOKEN = "test-owner-token"

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_settings():
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    yield
    app.dependency_overrides.clear()


def test_get_command_result_returns_not_found_for_unknown_command():
    result_registry = CommandResultRegistry()
    app.dependency_overrides[get_command_result_registry] = (
        lambda: result_registry
    )

    response = client.get(
        f"/commands/{uuid4()}/result",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": "Command result not found",
    }


def test_get_command_result_returns_recorded_result():
    result_registry = CommandResultRegistry()
    app.dependency_overrides[get_command_result_registry] = (
        lambda: result_registry
    )
    command_id = uuid4()
    websocket = object()
    command = OpenApplicationCommand(
        command_id=command_id,
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    expected_result = CommandResult(
        command_id=command_id,
        status="succeeded",
        detail="Fake command completed",
    )

    result_registry.expect(command, websocket)
    assert result_registry.accept_result(
        expected_result,
        "laptop-1",
        websocket,
    )

    response = client.get(
        f"/commands/{command_id}/result",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_result.model_dump(mode="json")


def test_get_command_result_rejects_missing_owner_token():
    response = client.get(
        f"/commands/{uuid4()}/result",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid development owner token",
    }


def test_get_command_status_returns_pending_for_dispatched_command():
    result_registry = CommandResultRegistry()
    app.dependency_overrides[get_command_result_registry] = (
        lambda: result_registry
    )
    command_id = uuid4()
    command = OpenApplicationCommand(
        command_id=command_id,
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    result_registry.expect(command, object())

    response = client.get(
        f"/commands/{command_id}",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "command_id": str(command_id),
        "status": "pending",
    }


def test_get_command_status_returns_completed_result():
    result_registry = CommandResultRegistry()
    app.dependency_overrides[get_command_result_registry] = (
        lambda: result_registry
    )
    command_id = uuid4()
    websocket = object()
    command = OpenApplicationCommand(
        command_id=command_id,
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    expected_result = CommandResult(
        command_id=command_id,
        status="succeeded",
        detail="Fake command completed",
    )

    result_registry.expect(command, websocket)
    assert result_registry.accept_result(
        expected_result,
        "laptop-1",
        websocket,
    )

    response = client.get(
        f"/commands/{command_id}",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_result.model_dump(mode="json")


def test_get_command_status_rejects_missing_owner_token():
    response = client.get(f"/commands/{uuid4()}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid development owner token",
    }


def test_get_command_status_rejects_invalid_owner_token():
    response = client.get(
        f"/commands/{uuid4()}",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": "Invalid development owner token",
    }


def test_get_command_status_returns_not_found_for_unknown_command():
    response = client.get(
        f"/commands/{uuid4()}",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": "Command not found",
    }


def test_get_command_status_returns_expired_for_overdue_command():
    result_registry = CommandResultRegistry()
    app.dependency_overrides[get_command_result_registry] = (
        lambda: result_registry
    )
    command_id = uuid4()
    command = OpenApplicationCommand(
        command_id=command_id,
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    result_registry.expect(command, object())
    result_registry._pending_commands[command_id].expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    response = client.get(
        f"/commands/{command_id}",
        headers={"Authorization": f"Bearer {TEST_OWNER_TOKEN}"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "command_id": str(command_id),
        "status": "expired",
    }
