from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.commands.models.command_record import CommandRecord


class ApprovalExpiredError(ValueError):
    """The proposal was expired at the time of the approval decision."""


class CommandRecordRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(self, record: CommandRecord) -> None:
        with Session(self.engine) as session:
            session.add(record)
            session.commit()

    def get(self, command_id: UUID) -> CommandRecord | None:
        with Session(self.engine) as session:
            return session.get(CommandRecord, command_id)

    def complete(
        self,
        command_id: UUID,
        *,
        state: str,
        detail: str | None,
        completed_at: datetime,
    ) -> None:
        with Session(self.engine) as session:
            record = session.get(CommandRecord, command_id)

            if record is None:
                raise LookupError("Cannot complete an unrecorded command")

            record.state = state
            record.detail = detail
            record.completed_at = completed_at
            session.commit()

    def decide_approval(
        self,
        command_id: UUID,
        *,
        approved: bool,
        decided_at: datetime,
    ) -> CommandRecord:
        with Session(self.engine) as session:
            result = session.execute(
                update(CommandRecord)
                .where(CommandRecord.command_id == command_id)
                .where(CommandRecord.state == "awaiting_approval")
                .where(CommandRecord.expires_at > decided_at)
                .values(
                    state="dispatched" if approved else "denied",
                    detail=None if approved else "Owner denied command",
                    completed_at=None if approved else decided_at,
                )
            )

            if result.rowcount != 1:
                record = session.get(CommandRecord, command_id)
                if record is None:
                    raise LookupError("Cannot decide an unrecorded command")
                if record.state == "awaiting_approval":
                    raise ApprovalExpiredError("Command has expired")
                raise ValueError("Command is not awaiting approval")

            session.commit()
            record = session.get(CommandRecord, command_id)
            assert record is not None
            return record
