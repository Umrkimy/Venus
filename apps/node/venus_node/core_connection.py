import asyncio
import json

from collections.abc import Callable
from json import JSONDecodeError

from venus_protocol.schemas.commands import CommandResult

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedOK

from venus_node.config import NodeSettings
from venus_protocol.schemas.connections import NodeHello


async def connect_to_core(
    settings: NodeSettings,
    on_connected: Callable[[NodeHello], None] | None = None,
    execute_payload: Callable[
        [dict[str, object]],
        CommandResult | None,
    ] | None = None,
) -> NodeHello:
    hello = NodeHello(device_id=settings.device_id)
    headers = {
        "Authorization": f"Bearer {settings.core_dev_token}",
    }

    async with connect(
        settings.core_url,
        additional_headers=headers,
    ) as websocket:
        await websocket.send(hello.model_dump_json())
        confirmed_hello = NodeHello.model_validate_json(
            await websocket.recv(),
        )

        if confirmed_hello.device_id != hello.device_id:
            raise ValueError("Core confirmed a different device")

        if on_connected is not None:
            on_connected(confirmed_hello)

        if execute_payload is None:
            await websocket.wait_closed()
        else:
            await receive_and_execute_command(
                websocket,
                execute_payload,
            )

    return confirmed_hello


async def keep_connected(
    settings: NodeSettings,
    on_connected: Callable[[NodeHello], None] | None = None,
    on_retry: Callable[[], None] | None = None,
    execute_payload: Callable[
        [dict[str, object]],
        CommandResult | None,
    ] | None = None,
) -> None:
    while True:
        try:
            await connect_to_core(
                settings,
                on_connected,
                execute_payload,
            )
        except OSError:
            if on_retry is not None:
                on_retry()

        await asyncio.sleep(1)


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
    try:
        message = await websocket.recv()
    except ConnectionClosedOK:
        # Core can stop while Node is waiting, so reconnect normally.
        return None

    result = execute_command_message(
        message,
        execute_payload,
    )

    if result is not None:
        await websocket.send(result.model_dump_json())

    return result
