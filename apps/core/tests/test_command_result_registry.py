from uuid import uuid4

from command_result_registry import CommandResultRegistry
from venus_protocol.schemas.commands import CommandResult


def test_command_result_registry_returns_recorded_result():
    registry = CommandResultRegistry()
    command_id = uuid4()
    result = CommandResult(
        command_id=command_id,
        status="succeeded",
        detail="Fake command completed",
    )

    registry.record(result)

    assert registry.get(command_id) is result