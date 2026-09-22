from datetime import datetime
from uuid import UUID

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.commands.models.command_record import CommandRecord


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