import logging
from datetime import datetime, timezone
from uuid import UUID

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
    ) -> None:
        self.device_id = device_id
        self.command_records = command_records

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

        if self.command_records.has_command(command.command_id):
            return CommandResult(
                command_id=command.command_id,
                status="denied",
                detail="Duplicate command",
            )

        self.command_records.record_command(
            CommandRecord(
                command_id=command.command_id,
                device_id=command.device_id,
                status="in_progress",
                detail=None,
                created_at=datetime.now(timezone.utc),
                completed_at=None,
            )
        )

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
