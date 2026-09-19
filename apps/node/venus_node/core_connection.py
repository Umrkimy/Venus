from websockets.asyncio.client import connect

from venus_node.config import NodeSettings
from venus_protocol.schemas.connections import NodeHello


async def connect_to_core(settings: NodeSettings) -> NodeHello:
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

    return confirmed_hello