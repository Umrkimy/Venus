from dataclasses import dataclass
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from fastapi import WebSocket
from venus_protocol.schemas.commands import CommandResult, OpenApplicationCommand


@dataclass
class DispatchedCommand:
    device_id: str
    websocket: WebSocket
    expires_at: datetime
    state: str = "dispatched"


class CommandResultRegistry:
    def __init__(self) -> None:
        self._dispatched_commands: dict[UUID, DispatchedCommand] = {}
        self._results: dict[UUID, CommandResult] = {}

    def expect(
        self,
        command: OpenApplicationCommand,
        websocket: WebSocket,
    ) -> None:
        self._dispatched_commands[command.command_id] = DispatchedCommand(
            device_id=command.device_id,
            websocket=websocket,
            expires_at=command.expires_at,
        )

    def accept_result(
        self,
        result: CommandResult,
        device_id: str,
        websocket: WebSocket,
        *,
        persist: Callable[[CommandResult], None] | None = None,
    ) -> bool:
        dispatched_command = self._dispatched_commands.get(result.command_id)

        if dispatched_command is None:
            return False

        if dispatched_command.device_id != device_id:
            return False

        if dispatched_command.websocket is not websocket:
            return False

        if dispatched_command.expires_at <= datetime.now(timezone.utc):
            return False

        if dispatched_command.state != "dispatched":
            return False

        # Publish only after durable storage succeeds. This synchronous section
        # must not yield between validating ownership and publishing the result.
        if persist is not None:
            persist(result)

        dispatched_command.state = "completed"
        self._results[result.command_id] = result
        return True

    def get(self, command_id: UUID) -> CommandResult | None:
        return self._results.get(command_id)

    def is_dispatched(self, command_id: UUID) -> bool:
        dispatched_command = self._dispatched_commands.get(command_id)
        return (
            dispatched_command is not None
            and dispatched_command.state == "dispatched"
        )

    def is_expired(self, command_id: UUID) -> bool:
        dispatched_command = self._dispatched_commands.get(command_id)
        return (
            dispatched_command is not None
            and dispatched_command.state == "dispatched"
            and dispatched_command.expires_at <= datetime.now(timezone.utc)
        )


command_result_registry = CommandResultRegistry()


def get_command_result_registry() -> CommandResultRegistry:
    return command_result_registry
