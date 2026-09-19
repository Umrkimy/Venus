import logging
from datetime import datetime, timezone
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from pydantic import ValidationError
from venus_protocol.schemas.commands import CommandResult, OpenApplicationCommand

from venus_node.models.command_record import CommandRecord
from venus_node.repositories.command_records import CommandRecordRepository

logger = logging.getLogger(__name__)


def execute_fake(command: OpenApplicationCommand) -> CommandResult:
    return CommandResult(
        command_id=command.command_id,
        status="succeeded",
        detail=f"Fake executor accepted {command.application_id}",
    )


class NodeExecutor:
    def __init__(
        self,
        device_id: str,
        command_records: CommandRecordRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.device_id = device_id
        self.command_records = command_records
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def execute_payload(self, payload: dict[str, object]) -> CommandResult | None:
        try:
            command_id = UUID(str(payload["command_id"]))
        except (KeyError, TypeError, ValueError):
            logger.warning("Discarded command without a valid command ID")
            return None

        try:
            command = OpenApplicationCommand.model_validate(payload)
        except ValidationError:
            return CommandResult(
                command_id=command_id,
                status="denied",
                detail="Invalid command",
            )

        if command.device_id != self.device_id:
            return CommandResult(
                command_id=command.command_id,
                status="denied",
                detail="Command targets another device",
            )
        try:
            claimed = self.command_records.record_command(
                CommandRecord(
                    command_id=command.command_id,
                    device_id=command.device_id,
                    status="in_progress",
                    detail=None,
                    created_at=datetime.now(timezone.utc),
                    completed_at=None,
                )
            )
        except (OSError, SQLAlchemyError):
            logger.exception("Unable to record command %s", command.command_id)
            return CommandResult(
                command_id=command.command_id,
                status="failed",
                detail="Unable to record command",
            )
        if not claimed:
            return CommandResult(
                command_id=command.command_id,
                status="denied",
                detail="Duplicate command",
            )

        execution_time = self.clock()
        if command.expires_at <= execution_time:
            result = CommandResult(
                command_id=command.command_id,
                status="denied",
                detail="Command expired before execution",
            )
            self.command_records.complete_command(
                command.command_id,
                status=result.status,
                detail=result.detail,
                completed_at=execution_time,
            )
            return result

        try:
            result = execute_fake(command)
        except Exception:
            result = CommandResult(
                command_id=command.command_id,
                status="failed",
                detail="Command execution failed",
            )

        self.command_records.complete_command(
            command.command_id,
            status=result.status,
            detail=result.detail,
            completed_at=datetime.now(timezone.utc),
        )
        return result
