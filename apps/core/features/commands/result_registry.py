from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import WebSocket
from venus_protocol.schemas.commands import CommandResult, OpenApplicationCommand


@dataclass
class PendingCommand:
    device_id: str
    websocket: WebSocket
    expires_at: datetime
    state: str = "pending"


class CommandResultRegistry:
    def __init__(self) -> None:
        self._pending_commands: dict[UUID, PendingCommand] = {}
        self._results: dict[UUID, CommandResult] = {}

    def expect(
        self,
        command: OpenApplicationCommand,
        websocket: WebSocket,
    ) -> None:
        self._pending_commands[command.command_id] = PendingCommand(
            device_id=command.device_id,
            websocket=websocket,
            expires_at=command.expires_at,
        )

    def accept_result(
        self,
        result: CommandResult,
        device_id: str,
        websocket: WebSocket,
    ) -> bool:
        pending_command = self._pending_commands.get(result.command_id)

        if pending_command is None:
            return False

        if pending_command.device_id != device_id:
            return False

        if pending_command.websocket is not websocket:
            return False

        if pending_command.expires_at <= datetime.now(timezone.utc):
            return False

        if pending_command.state != "pending":
            return False

        pending_command.state = "completed"
        self._results[result.command_id] = result
        return True

    def get(self, command_id: UUID) -> CommandResult | None:
        return self._results.get(command_id)

    def is_pending(self, command_id: UUID) -> bool:
        pending_command = self._pending_commands.get(command_id)
        return pending_command is not None and pending_command.state == "pending"

    def is_expired(self, command_id: UUID) -> bool:
        pending_command = self._pending_commands.get(command_id)
        return (
            pending_command is not None
            and pending_command.state == "pending"
            and pending_command.expires_at <= datetime.now(timezone.utc)
        )


command_result_registry = CommandResultRegistry()


def get_command_result_registry() -> CommandResultRegistry:
    return command_result_registry
