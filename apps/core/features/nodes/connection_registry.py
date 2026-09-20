import asyncio

from fastapi import WebSocket, status


class NodeConnectionRegistry:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        device_id: str,
        websocket: WebSocket,
    ) -> None:
        async with self._lock:
            old_websocket = self._connections.get(device_id)
            self._connections[device_id] = websocket

        if old_websocket is not None:
            await old_websocket.close(
                code=status.WS_1000_NORMAL_CLOSURE,
            )

    def get(self, device_id: str) -> WebSocket | None:
        return self._connections.get(device_id)

    async def unregister(
        self,
        device_id: str,
        websocket: WebSocket,
    ) -> None:
        async with self._lock:
            # An old socket must not remove its newer replacement.
            if self._connections.get(device_id) is websocket:
                del self._connections[device_id]


connection_registry = NodeConnectionRegistry()

def get_connection_registry() -> NodeConnectionRegistry:
    return connection_registry
