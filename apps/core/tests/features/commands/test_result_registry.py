from datetime import datetime, timedelta, timezone
from uuid import uuid4

from features.commands.result_registry import CommandResultRegistry
from venus_protocol.schemas.commands import CommandResult, OpenApplicationCommand


def test_command_result_registry_returns_expected_result():
    registry = CommandResultRegistry()
    command_id = uuid4()
    websocket = object()
    command = OpenApplicationCommand(
        command_id=command_id,
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    result = CommandResult(
        command_id=command_id,
        status="succeeded",
        detail="Fake command completed",
    )

    registry.expect(command, websocket)

    accepted = registry.accept_result(
        result,
        "laptop-1",
        websocket,
    )

    assert accepted is True
    assert registry.get(command_id) is result
