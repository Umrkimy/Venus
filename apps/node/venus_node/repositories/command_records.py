from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from venus_node.models.base import Base
from venus_node.models.command_record import CommandRecord


class CommandRecordRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        Base.metadata.create_all(self.engine)

    def has_command(self, command_id: UUID) -> bool:
        statement = select(CommandRecord).where(
            CommandRecord.command_id == command_id
        )

        with Session(self.engine) as session:
            return session.scalar(statement) is not None

    def record_command(self, command: CommandRecord) -> None:
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(command)
            session.commit()

    def complete_command(
        self,
        command_id: UUID,
        *,
        status: str,
        detail: str | None,
        completed_at: datetime,
    ) -> None:
        with Session(self.engine) as session:
            command = session.get(CommandRecord, command_id)
            if command is None:
                raise LookupError("Cannot complete an unrecorded command")

            command.status = status
            command.detail = detail
            command.completed_at = completed_at
            session.commit()

    def close(self) -> None:
        self.engine.dispose()
