from datetime import datetime, timedelta, timezone
from uuid import uuid4

from features.commands.models.command_record import CommandRecord


def test_new_command_record_starts_pending():
    record = CommandRecord(
        command_id=uuid4(),
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    assert record.state == "pending"