import pytest
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
    assert stored_record.state == "dispatched"

    engine.dispose()


def test_repository_completes_command_record() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = CommandRecordRepository(engine)

    command_id = uuid4()
    repository.create(
        CommandRecord(
            command_id=command_id,
            device_id="PC-Umar",
            application_id="spotify",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
    )
    completed_at = datetime.now(timezone.utc)

    repository.complete(
        command_id,
        state="succeeded",
        detail="Fake executor accepted spotify",
        completed_at=completed_at,
    )

    stored_record = repository.get(command_id)

    assert stored_record is not None
    assert stored_record.state == "succeeded"
    assert stored_record.detail == "Fake executor accepted spotify"
    assert stored_record.completed_at == completed_at.replace(tzinfo=None)

    engine.dispose()


def test_repository_rejects_completing_unrecorded_command() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = CommandRecordRepository(engine)

    with pytest.raises(LookupError):
        repository.complete(
            uuid4(),
            state="succeeded",
            detail="Fake executor accepted spotify",
            completed_at=datetime.now(timezone.utc),
        )

    engine.dispose()
