import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


from features.commands.models.command_record import CommandRecord
from features.commands.repository import CommandRecordRepository
from storage.base import Base
from storage.database import create_database_engine


@pytest.mark.parametrize("approved", [True, False])
@pytest.mark.parametrize("seconds_after_expiry", [0, 1])
def test_repository_rejects_decision_at_or_after_expiry(
    approved: bool, seconds_after_expiry: int,
) -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = CommandRecordRepository(engine)
    command_id = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    try:
        repository.create(CommandRecord(
            command_id=command_id,
            device_id="PC-Umar",
            application_id="spotify",
            expires_at=expires_at,
        ))
        with pytest.raises(ValueError, match="expired"):
            repository.decide_approval(
                command_id,
                approved=approved,
                decided_at=expires_at + timedelta(seconds=seconds_after_expiry),
            )
        stored = repository.get(command_id)
        assert stored is not None
        assert stored.state == "awaiting_approval"
        assert stored.completed_at is None
    finally:
        engine.dispose()


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
    assert stored_record.state == "awaiting_approval"

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


def test_repository_accepts_only_one_concurrent_approval_decision(tmp_path):
    database_path = tmp_path / "core.db"
    engine = create_database_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}"
    )
    Base.metadata.create_all(engine)
    repository = CommandRecordRepository(engine)

    command_id = uuid4()
    now = datetime.now(timezone.utc)
    repository.create(
        CommandRecord(
            command_id=command_id,
            device_id="PC-Umar",
            application_id="spotify",
            expires_at=now + timedelta(minutes=5),
        )
    )

    barrier = Barrier(2)

    def decide(approved: bool):
        barrier.wait(timeout=5)
        try:
            repository.decide_approval(
                command_id,
                approved=approved,
                decided_at=now,
            )
            return approved, "accepted"
        except ValueError:
            return approved, "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(decide, True)
        second = pool.submit(decide, False)
        outcomes = [first.result(timeout=10), second.result(timeout=10)]

    assert sorted(outcome for _, outcome in outcomes) == [
        "accepted",
        "rejected",
    ]

    winning_approval = next(
        approved for approved, outcome in outcomes if outcome == "accepted"
    )
    stored_record = repository.get(command_id)
    assert stored_record is not None
    assert stored_record.state == (
        "dispatched" if winning_approval else "denied"
    )

    engine.dispose()
