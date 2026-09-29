import asyncio

from collections.abc import Callable

from venus_protocol.schemas.commands import CommandResult

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosedError

from venus_node.config import NodeSettings
from venus_node.connection.messages import receive_and_execute_commands
from venus_node.commands.start_apps import StartApp
from venus_protocol.schemas.connections import NodeApp, NodeHello


async def connect_to_core(
    settings: NodeSettings,
    on_connected: Callable[[NodeHello], None] | None = None,
    execute_payload: Callable[
        [dict[str, object]],
        CommandResult | None,
    ] | None = None,
    list_apps: Callable[[], list[StartApp]] | None = None,
) -> NodeHello:
    apps = [] if list_apps is None else [
        NodeApp(name=app.name, app_id=app.app_id) for app in list_apps()
    ]
    hello = NodeHello(device_id=settings.device_id, apps=apps)
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
            await receive_and_execute_commands(
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
    list_apps: Callable[[], list[StartApp]] | None = None,
) -> None:
    while True:
        try:
            await connect_to_core(
                settings,
                on_connected,
                execute_payload,
                list_apps=list_apps,
            )
        except (OSError, ConnectionClosedError):
            if on_retry is not None:
                on_retry()

        # Local connections can drop normally, so wait briefly before reconnecting.
        await asyncio.sleep(1)
