import json

from collections.abc import Callable
from json import JSONDecodeError

from venus_protocol.schemas.commands import CommandResult
from websockets.exceptions import ConnectionClosedOK


def execute_command_message(
    message: str,
    execute_payload: Callable[
        [dict[str, object]],
        CommandResult | None,
    ],
) -> CommandResult | None:
    try:
        payload = json.loads(message)
    except JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    return execute_payload(payload)


async def receive_and_execute_command(
    websocket,
    execute_payload: Callable[
        [dict[str, object]],
        CommandResult | None,
    ],
) -> CommandResult | None:
    message = await websocket.recv()

    result = execute_command_message(message, execute_payload)

    if result is not None:
        await websocket.send(result.model_dump_json())

    return result


async def receive_and_execute_commands(
    websocket,
    execute_payload: Callable[
        [dict[str, object]],
        CommandResult | None,
    ],
) -> None:
    try:
        while True:
            await receive_and_execute_command(websocket, execute_payload)
    except ConnectionClosedOK:
        # Core can stop while Node is waiting, so reconnect normally.
        return
