from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.commands.models.command_record import CommandRecord


class ApprovalExpiredError(ValueError):
    """The proposal was expired at the time of the approval decision."""


class CommandNotDispatchedError(ValueError):
    """The command is no longer waiting for a Node result."""


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
            result = session.execute(
                update(CommandRecord)
                .where(CommandRecord.command_id == command_id)
                .where(CommandRecord.state == "dispatched")
                .values(
                    state=state,
                    detail=detail,
                    completed_at=completed_at,
                )
            )

            if result.rowcount != 1:
                record = session.get(CommandRecord, command_id)

                if record is None:
                    raise LookupError("Cannot complete an unrecorded command")

                raise CommandNotDispatchedError(
                    "The command is no longer waiting for a Node result"
                )

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

    def mark_overdue_dispatched_unknown(
        self,
        command_id: UUID,
        *,
        checked_at: datetime,
    ) -> bool:
        with Session(self.engine) as session:
            result = session.execute(
                update(CommandRecord)
                .where(CommandRecord.command_id == command_id)
                .where(CommandRecord.state == "dispatched")
                .where(CommandRecord.expires_at <= checked_at)
                .values(state="unknown", completed_at=checked_at)
            )
            if result.rowcount != 1:
                return False
            session.commit()
            return True

    def mark_all_dispatched_unknown(self, *, checked_at: datetime) -> int:
        with Session(self.engine) as session:
            result = session.execute(
                update(CommandRecord)
                .where(CommandRecord.state == "dispatched")
                .values(
                    state="unknown",
                    completed_at=checked_at,
                    detail="Core restarted before a result arrived",
                )
            )

            session.commit()
            return result.rowcount
