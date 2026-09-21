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