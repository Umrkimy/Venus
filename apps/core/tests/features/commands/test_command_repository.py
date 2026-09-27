import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy.orm import Session


from features.commands.models.command_record import CommandRecord
from features.commands.repository import (
    CommandNotDispatchedError,
    CommandRecordRepository,
)
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


def test_repository_marks_all_dispatched_unknown_on_recovery() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = CommandRecordRepository(engine)

    checked_at = datetime.now(timezone.utc)

    try:
        dispatched_id = uuid4()
        awaiting_approval_id = uuid4()
        succeeded_id = uuid4()

        dispatched_record = CommandRecord(
            command_id=dispatched_id,
            device_id="PC-Umar",
            application_id="spotify",
            state="dispatched",
            expires_at=checked_at + timedelta(minutes=5),
        )

        awaiting_approval_record = CommandRecord(
            command_id=awaiting_approval_id,
            device_id="PC-Umar",
            application_id="spotify",
            state="awaiting_approval",
            expires_at=checked_at + timedelta(minutes=5),
        )

        succeeded_record = CommandRecord(
            command_id=succeeded_id,
            device_id="PC-Umar",
            application_id="spotify",
            state="dispatched",
            expires_at=checked_at + timedelta(minutes=5),
        )

        with Session(engine) as session:
            session.add_all(
                [
                    dispatched_record,
                    awaiting_approval_record,
                    succeeded_record,
                ]
            )
            session.commit()

        repository.complete(
            succeeded_id,
            state="succeeded",
            detail="Spotify opened",
            completed_at=checked_at,
        )

        updated_count = repository.mark_all_dispatched_unknown(
            checked_at=checked_at,
        )

        assert updated_count == 1

        with Session(engine) as session:
            dispatched = session.get(CommandRecord, dispatched_id)
            awaiting_approval = session.get(CommandRecord, awaiting_approval_id)
            succeeded = session.get(CommandRecord, succeeded_id)

            assert dispatched is not None
            assert awaiting_approval is not None
            assert succeeded is not None

            assert dispatched.state == "unknown"
            assert dispatched.completed_at == checked_at.replace(tzinfo=None)
            assert dispatched.detail == "Core restarted before a result arrived"

            assert awaiting_approval.state == "awaiting_approval"

            assert succeeded.state == "succeeded"
            assert succeeded.detail == "Spotify opened"
    finally:
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
            state="dispatched",
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


def test_repository_marks_overdue_dispatched_command_unknown() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = CommandRecordRepository(engine)
    command_id = uuid4()
    checked_at = datetime.now(timezone.utc)

    try:
        repository.create(
            CommandRecord(
                command_id=command_id,
                device_id="PC-Umar",
                application_id="spotify",
                state="dispatched",
                expires_at=checked_at - timedelta(seconds=1),
            )
        )

        changed = repository.mark_overdue_dispatched_unknown(
            command_id, checked_at=checked_at
        )
        stored = repository.get(command_id)

        assert changed is True
        assert stored is not None
        assert stored.state == "unknown"
        assert stored.completed_at == checked_at.replace(tzinfo=None)
    finally:
        engine.dispose()


def test_repository_does_not_replace_completed_result_with_unknown() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = CommandRecordRepository(engine)
    command_id = uuid4()
    checked_at = datetime.now(timezone.utc)
    completed_at = checked_at - timedelta(seconds=2)

    try:
        repository.create(
            CommandRecord(
                command_id=command_id,
                device_id="PC-Umar",
                application_id="spotify",
                state="dispatched",
                expires_at=checked_at - timedelta(seconds=1),
            )
        )
        repository.complete(
            command_id,
            state="succeeded",
            detail="Fake command completed",
            completed_at=completed_at,
        )

        changed = repository.mark_overdue_dispatched_unknown(
            command_id, checked_at=checked_at
        )
        stored = repository.get(command_id)

        assert changed is False
        assert stored is not None
        assert stored.state == "succeeded"
        assert stored.detail == "Fake command completed"
        assert stored.completed_at == completed_at.replace(tzinfo=None)
    finally:
        engine.dispose()


def test_repository_rejects_completing_unknown_command() -> None:
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = CommandRecordRepository(engine)
    command_id = uuid4()
    checked_at = datetime.now(timezone.utc)

    try:
        repository.create(
            CommandRecord(
                command_id=command_id,
                device_id="PC-Umar",
                application_id="spotify",
                state="dispatched",
                expires_at=checked_at - timedelta(seconds=1),
            )
        )
        repository.mark_overdue_dispatched_unknown(
            command_id, checked_at=checked_at
        )

        with pytest.raises(CommandNotDispatchedError):
            repository.complete(
                command_id,
                state="succeeded",
                detail="Late fake result",
                completed_at=checked_at + timedelta(seconds=1),
            )

        stored = repository.get(command_id)
        assert stored is not None
        assert stored.state == "unknown"
        assert stored.detail is None
    finally:
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
