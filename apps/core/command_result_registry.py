from uuid import UUID

from venus_protocol.schemas.commands import CommandResult


class CommandResultRegistry:
    def __init__(self) -> None:
        self._results: dict[UUID, CommandResult] = {}

    def record(self, result: CommandResult) -> None:
        self._results[result.command_id] = result

    def get(self, command_id: UUID) -> CommandResult | None:
        return self._results.get(command_id)


command_result_registry = CommandResultRegistry()


def get_command_result_registry() -> CommandResultRegistry:
    return command_result_registry