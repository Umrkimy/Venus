from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from venus_node.executor import NodeExecutor, execute_fake
from venus_node.repositories.command_records import CommandRecordRepository
from venus_protocol.schemas.commands import OpenApplicationCommand


def test_execute_fake_returns_success_for_spotify():
    command = OpenApplicationCommand(
        command_id=uuid4(),
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(minutes=5),
    )

    result = execute_fake(command)

    assert result.command_id == command.command_id
    assert result.status == "succeeded"
    assert result.detail == "Fake executor accepted spotify"


def test_execute_payload_denies_invalid_command_with_valid_id(tmp_path):
    command_id = uuid4()
    executor = NodeExecutor(
        device_id="laptop-1",
        command_records=CommandRecordRepository(tmp_path / "node.db"),
    )

    result = executor.execute_payload(
        {
            "command_id": str(command_id),
            "device_id": "laptop-1",
            "application_id": "brave",
            "expires_at": datetime.now(
                ZoneInfo("Asia/Kuala_Lumpur")
            ) + timedelta(minutes=5),
        }
    )

    assert result is not None
    assert result.command_id == command_id
    assert result.status == "denied"
    assert result.detail == "Invalid command"


def test_execute_payload_discards_invalid_command_id(tmp_path):
    executor = NodeExecutor(
        device_id="laptop-1",
        command_records=CommandRecordRepository(tmp_path / "node.db"),
    )
    result = executor.execute_payload({"command_id": "not-a-uuid"})

    assert result is None


def test_execute_payload_targeting_another_device(tmp_path):
    command_id = uuid4()
    executor = NodeExecutor(
        device_id="laptop-2",
        command_records=CommandRecordRepository(tmp_path / "node.db"),
    )

    result = executor.execute_payload(
        {
            "command_id": str(command_id),
            "device_id": "laptop-1",
            "application_id": "spotify",
            "expires_at": datetime.now(
                ZoneInfo("Asia/Kuala_Lumpur")
            ) + timedelta(minutes=5),
        }
    )

    assert result is not None
    assert result.status == "denied"
    assert result.detail == "Command targets another device"


def test_executor_denies_duplicate_command_id_after_restart(tmp_path):
    command_id = uuid4()
    database_path = tmp_path / "node.db"
    first_executor = NodeExecutor(
        device_id="laptop-1",
        command_records=CommandRecordRepository(database_path),
    )

    payload = {
        "command_id": str(command_id),
        "device_id": "laptop-1",
        "application_id": "spotify",
        "expires_at": datetime.now(
            ZoneInfo("Asia/Kuala_Lumpur")
        ) + timedelta(minutes=5),
    }

    first_result = first_executor.execute_payload(payload)
    second_executor = NodeExecutor(
        device_id="laptop-1",
        command_records=CommandRecordRepository(database_path),
    )
    second_result = second_executor.execute_payload(payload)

    assert first_result is not None
    assert first_result.status == "succeeded"
    assert second_result is not None
    assert second_result.status == "denied"
    assert second_result.detail == "Duplicate command"
