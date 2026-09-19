from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from venus_node.models.command_record import CommandRecord
from venus_node.repositories.command_records import (
    CommandRecordRepository,
)


def test_has_command_is_false_for_unknown_command(tmp_path):
    database_path = tmp_path / "node.db"
    repository = CommandRecordRepository(database_path)

    assert repository.has_command(uuid4()) is False


def test_record_command_makes_command_findable(tmp_path):
    database_path = tmp_path / "node.db"
    repository = CommandRecordRepository(database_path)

    command = CommandRecord(
        command_id=uuid4(),
        device_id="laptop-1",
        status="in_progress",
        detail=None,
        created_at=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")),
        completed_at=None,
    )

    assert repository.record_command(command) is True

    second_repository = CommandRecordRepository(database_path)
    assert second_repository.has_command(command.command_id) is True
