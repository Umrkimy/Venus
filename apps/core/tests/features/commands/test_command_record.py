from datetime import datetime, timedelta, timezone
from uuid import uuid4

from features.commands.models.command_record import CommandRecord


def test_new_command_record_starts_dispatched():
    record = CommandRecord(
        command_id=uuid4(),
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    assert record.state == "dispatched"


def test_new_command_record_has_no_result_yet():
    record = CommandRecord(
        command_id=uuid4(),
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    assert record.detail is None
    assert record.completed_at is None
