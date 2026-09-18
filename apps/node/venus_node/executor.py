import logging
from uuid import UUID

from pydantic import ValidationError
from venus_protocol.commands import CommandResult, OpenApplicationCommand

logger = logging.getLogger(__name__)


def execute_fake(command: OpenApplicationCommand) -> CommandResult:
    return CommandResult(
        command_id=command.command_id,
        status="succeeded",
        detail=f"Fake executor accepted {command.application_id}",
    )


def execute_payload(
    payload: dict[str, object],
    *,
    node_device_id: str,
) -> CommandResult | None:
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

    if command.device_id != node_device_id:
        return CommandResult(
            command_id=command.command_id,
            status="denied",
            detail="Command targets another device",
        )

    return execute_fake(command)
