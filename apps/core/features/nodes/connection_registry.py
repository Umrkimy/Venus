import asyncio

from fastapi import WebSocket, status

from venus_protocol.schemas.connections import NodeApp


class NodeConnectionRegistry:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}
        self._apps: dict[str, list[NodeApp]] = {}
        self._projects: dict[str, list[str]] = {}
        self._lock = asyncio.Lock()

    async def register(
        self,
        device_id: str,
        websocket: WebSocket,
        apps: list[NodeApp] | None = None,
        projects: list[str] | None = None,
    ) -> None:
        async with self._lock:
            old_websocket = self._connections.get(device_id)
            self._connections[device_id] = websocket
            self._apps[device_id] = list(apps or [])
            self._projects[device_id] = list(projects or [])

        if old_websocket is not None:
            await old_websocket.close(
                code=status.WS_1000_NORMAL_CLOSURE,
            )

    def get(self, device_id: str) -> WebSocket | None:
        return self._connections.get(device_id)

    def apps_for(self, device_id: str) -> list[NodeApp] | None:
        # None means the Node is not connected
        if device_id not in self._connections:
            return None
        return list(self._apps.get(device_id, []))

    def projects_for(self, device_id: str) -> list[str] | None:
        # None means the Node is not connected
        if device_id not in self._connections:
            return None
        return list(self._projects.get(device_id, []))

    def connected_device_ids(self) -> list[str]:
        return sorted(self._connections)

    async def unregister(
        self,
        device_id: str,
        websocket: WebSocket,
    ) -> None:
        async with self._lock:
            # An old socket must not remove its newer replacement.
            if self._connections.get(device_id) is websocket:
                del self._connections[device_id]
                self._apps.pop(device_id, None)
                self._projects.pop(device_id, None)


connection_registry = NodeConnectionRegistry()

def get_connection_registry() -> NodeConnectionRegistry:
    return connection_registry
