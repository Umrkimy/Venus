from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from venus_node.commands.executor import NodeExecutor, execute_fake
from venus_node.config import NodeSettings
from venus_node.commands.launcher import create_spotify_command_executor
from venus_node.storage.repositories.command_records import CommandRecordRepository
from venus_protocol.schemas.commands import CommandResult, OpenApplicationCommand
from venus_node.storage.models.command_record import CommandRecord


class SynchronizedCommandRecordRepository(CommandRecordRepository):
    def __init__(self, *args, barrier: Barrier, **kwargs):
        super().__init__(*args, **kwargs)
        self.barrier = barrier

    def record_command(self, command):
        self.barrier.wait()
        return super().record_command(command)


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


def test_executor_denies_simultaneous_duplicate_command_id(tmp_path, monkeypatch):
    command_id = uuid4()
    database_path = tmp_path / "node.db"
    barrier = Barrier(2)
    fake_call_lock = Lock()
    fake_call_count = 0

    def fake_once(command: OpenApplicationCommand) -> CommandResult:
        nonlocal fake_call_count
        with fake_call_lock:
            fake_call_count += 1

        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="Fake executor accepted spotify",
        )

    monkeypatch.setattr("venus_node.commands.executor.execute_fake", fake_once)

    first_executor = NodeExecutor(
        device_id="laptop-1",
        command_records=SynchronizedCommandRecordRepository(
            database_path,
            barrier=barrier,
        ),
    )
    second_executor = NodeExecutor(
        device_id="laptop-1",
        command_records=SynchronizedCommandRecordRepository(
            database_path,
            barrier=barrier,
        ),
    )
    payload = {
        "command_id": str(command_id),
        "device_id": "laptop-1",
        "application_id": "spotify",
        "expires_at": datetime.now(
            ZoneInfo("Asia/Kuala_Lumpur")
        ) + timedelta(minutes=5),
    }

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(first_executor.execute_payload, payload)
        second_future = pool.submit(second_executor.execute_payload, payload)
        results = [first_future.result(), second_future.result()]

    assert all(result is not None for result in results)
    assert sorted(result.status for result in results) == [
        "denied",
        "succeeded",
    ]
    duplicate_result = next(result for result in results if result.status == "denied")
    assert duplicate_result.detail == "Duplicate command"
    assert fake_call_count == 1


def test_executor_returns_failed_result_when_execution_raises(
    tmp_path,
    monkeypatch,
):
    def raise_execution_error(command: OpenApplicationCommand) -> CommandResult:
        raise RuntimeError("Spotify did not respond")

    monkeypatch.setattr(
        "venus_node.commands.executor.execute_fake",
        raise_execution_error,
    )

    command_id = uuid4()
    database_path = tmp_path / "node.db"
    executor = NodeExecutor(
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

    result = executor.execute_payload(payload)

    assert result is not None
    assert result.status == "failed"
    assert result.detail == "Command execution failed"

    second_repository = CommandRecordRepository(database_path)
    record = second_repository.get_command(command_id)

    assert record is not None
    assert record.status == "failed"
    assert record.detail == "Command execution failed"
    assert record.completed_at is not None

def test_executor_does_not_replay_in_progress_command_after_restart(
    tmp_path,
    monkeypatch,
):
    command_id = uuid4()
    database_path = tmp_path / "node.db"
    fake_call_count = 0

    def unexpected_fake(command: OpenApplicationCommand) -> CommandResult:
        nonlocal fake_call_count
        fake_call_count += 1
        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="This should not run",
        )

    monkeypatch.setattr(
        "venus_node.commands.executor.execute_fake",
        unexpected_fake,
    )

    first_repository = CommandRecordRepository(database_path)
    first_repository.record_command(
        CommandRecord(
            command_id=command_id,
            device_id="laptop-1",
            status="in_progress",
            detail=None,
            created_at=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
            completed_at=None,
        )
    )
    first_repository.close()

    restarted_executor = NodeExecutor(
        device_id="laptop-1",
        command_records=CommandRecordRepository(database_path),
    )
    result = restarted_executor.execute_payload(
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
    assert result.detail == "Duplicate command"
    assert fake_call_count == 0


def test_executor_denies_command_expired_before_execution(
    tmp_path,
    monkeypatch,
):
    command_id = uuid4()
    expires_at = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(
        minutes=5
    )
    fake_execution_time = expires_at + timedelta(seconds=1)
    database_path = tmp_path / "node.db"
    fake_call_count = 0

    def unexpected_fake(command: OpenApplicationCommand) -> CommandResult:
        nonlocal fake_call_count
        fake_call_count += 1
        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="This should not run",
        )

    monkeypatch.setattr(
        "venus_node.commands.executor.execute_fake",
        unexpected_fake,
    )

    executor = NodeExecutor(
        device_id="laptop-1",
        command_records=CommandRecordRepository(database_path),
        clock=lambda: fake_execution_time,
    )
    result = executor.execute_payload(
        {
            "command_id": str(command_id),
            "device_id": "laptop-1",
            "application_id": "spotify",
            "expires_at": expires_at,
        }
    )

    assert result is not None
    assert result.status == "denied"
    assert result.detail == "Command expired before execution"
    assert fake_call_count == 0

    record = CommandRecordRepository(database_path).get_command(command_id)
    assert record is not None
    assert record.status == "denied"
    assert record.completed_at is not None


def test_executor_does_not_execute_when_claim_storage_fails(
    tmp_path,
    monkeypatch,
):
    fake_call_count = 0

    def storage_failure(command: CommandRecord) -> bool:
        raise OSError("disk unavailable")

    def unexpected_fake(command: OpenApplicationCommand) -> CommandResult:
        nonlocal fake_call_count
        fake_call_count += 1
        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="This should not run",
        )

    repository = CommandRecordRepository(tmp_path / "node.db")
    monkeypatch.setattr(repository, "record_command", storage_failure)
    monkeypatch.setattr(
        "venus_node.commands.executor.execute_fake",
        unexpected_fake,
    )

    executor = NodeExecutor(
        device_id="laptop-1",
        command_records=repository,
    )
    result = executor.execute_payload(
        {
            "command_id": str(uuid4()),
            "device_id": "laptop-1",
            "application_id": "spotify",
            "expires_at": datetime.now(
                ZoneInfo("Asia/Kuala_Lumpur")
            ) + timedelta(minutes=5),
        }
    )

    assert result is not None
    assert result.status == "failed"
    assert result.detail == "Unable to record command"
    assert fake_call_count == 0


def test_executor_does_not_report_result_when_completion_storage_fails(
    tmp_path,
    monkeypatch,
):
    command_id = uuid4()
    database_path = tmp_path / "node.db"
    fake_call_count = 0

    def completion_storage_failure(*args, **kwargs) -> None:
        raise OSError("disk unavailable")

    def fake_once(command: OpenApplicationCommand) -> CommandResult:
        nonlocal fake_call_count
        fake_call_count += 1
        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="Fake executor accepted spotify",
        )

    repository = CommandRecordRepository(database_path)
    monkeypatch.setattr(
        repository,
        "complete_command",
        completion_storage_failure,
    )
    monkeypatch.setattr(
        "venus_node.commands.executor.execute_fake",
        fake_once,
    )

    executor = NodeExecutor(
        device_id="laptop-1",
        command_records=repository,
    )

    with pytest.raises(OSError, match="disk unavailable"):
        executor.execute_payload(
            {
                "command_id": str(command_id),
                "device_id": "laptop-1",
                "application_id": "spotify",
                "expires_at": datetime.now(
                    ZoneInfo("Asia/Kuala_Lumpur")
                ) + timedelta(minutes=5),
            }
        )

    assert fake_call_count == 1

    repository.close()
    second_repository = CommandRecordRepository(database_path)
    record = second_repository.get_command(command_id)

    assert record is not None
    assert record.status == "in_progress"
    assert record.completed_at is None

    restarted_executor = NodeExecutor(
        device_id="laptop-1",
        command_records=second_repository,
    )
    replay_result = restarted_executor.execute_payload(
        {
            "command_id": str(command_id),
            "device_id": "laptop-1",
            "application_id": "spotify",
            "expires_at": datetime.now(
                ZoneInfo("Asia/Kuala_Lumpur")
            ) + timedelta(minutes=5),
        }
    )

    assert replay_result is not None
    assert replay_result.status == "denied"
    assert replay_result.detail == "Duplicate command"
    assert fake_call_count == 1


def test_executor_uses_injected_command_executor(tmp_path):
    command_id = uuid4()
    executed_command_ids = []

    def recording_executor(command: OpenApplicationCommand) -> CommandResult:
        executed_command_ids.append(command.command_id)

        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="Recording executor accepted spotify",
        )

    executor = NodeExecutor(
        device_id="laptop-1",
        command_records=CommandRecordRepository(tmp_path / "node.db"),
        command_executor=recording_executor,
    )

    result = executor.execute_payload(
        {
            "command_id": str(command_id),
            "device_id": "laptop-1",
            "application_id": "spotify",
            "expires_at": datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
            + timedelta(minutes=5),
        }
    )

    assert result is not None
    assert result.status == "succeeded"
    assert executed_command_ids == [command_id]


def test_executor_runs_configured_spotify_launcher(tmp_path):
    command_id = uuid4()
    launched_targets: list[str] = []
    command_executor = create_spotify_command_executor(
        settings=NodeSettings(
            device_id="laptop-1",
            spotify_target="spotify:",
            core_dev_token="test-node-token",
            core_url="ws://core.test/nodes/connect",
        ),
        start_target=launched_targets.append,
    )
    executor = NodeExecutor(
        device_id="laptop-1",
        command_records=CommandRecordRepository(tmp_path / "node.db"),
        command_executor=command_executor,
    )

    result = executor.execute_payload(
        {
            "command_id": str(command_id),
            "device_id": "laptop-1",
            "application_id": "spotify",
            "expires_at": datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
            + timedelta(minutes=5),
        }
    )

    assert result is not None
    assert result.status == "succeeded"
    assert launched_targets == ["spotify:"]


def test_executor_records_failed_result_when_spotify_launch_fails(tmp_path):
    command_id = uuid4()

    def failing_start_target(target: str) -> None:
        raise OSError("Windows failure")

    repository = CommandRecordRepository(tmp_path / "node.db")
    command_executor = create_spotify_command_executor(
        settings=NodeSettings(
            device_id="laptop-1",
            spotify_target="spotify:",
            core_dev_token="test-node-token",
            core_url="ws://core.test/nodes/connect",
        ),
        start_target=failing_start_target,
    )
    executor = NodeExecutor(
        device_id="laptop-1",
        command_records=repository,
        command_executor=command_executor,
    )

    result = executor.execute_payload(
        {
            "command_id": str(command_id),
            "device_id": "laptop-1",
            "application_id": "spotify",
            "expires_at": datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
            + timedelta(minutes=5),
        }
    )

    assert result is not None
    assert result.status == "failed"
    assert result.detail == "Command execution failed"

    record = repository.get_command(command_id)
    assert record is not None
    assert record.status == "failed"
    assert record.completed_at is not None
