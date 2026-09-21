from datetime import datetime, timedelta, timezone
from uuid import uuid4

from features.commands.models.command_record import CommandRecord
from features.commands.repository import CommandRecordRepository
from storage.base import Base
from storage.database import create_database_engine


def test_repository_stores_and_gets_command_record() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = CommandRecordRepository(engine)

    command_id = uuid4()
    record = CommandRecord(
        command_id=command_id,
        device_id="PC-Umar",
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )

    repository.create(record)

    stored_record = repository.get(command_id)

    assert stored_record is not None
    assert stored_record.command_id == command_id
    assert stored_record.device_id == "PC-Umar"
    assert stored_record.application_id == "spotify"
    assert stored_record.state == "pending"

    engine.dispose()