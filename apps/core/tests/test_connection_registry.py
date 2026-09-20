import asyncio

from fastapi import status

from connection_registry import NodeConnectionRegistry


def test_register_replaces_existing_connection():
    class FakeWebSocket:
        def __init__(self):
            self.close_codes: list[int] = []

        async def close(self, code: int):
            self.close_codes.append(code)

    async def register_connections():
        registry = NodeConnectionRegistry()
        old_websocket = FakeWebSocket()
        new_websocket = FakeWebSocket()

        await registry.register("PC-Umar", old_websocket)
        await registry.register("PC-Umar", new_websocket)

        return registry, old_websocket, new_websocket

    registry, old_websocket, new_websocket = asyncio.run(
        register_connections(),
    )

    assert registry.get("PC-Umar") is new_websocket
    assert old_websocket.close_codes == [
        status.WS_1000_NORMAL_CLOSURE,
    ]
    assert new_websocket.close_codes == []


def test_unregister_keeps_newer_replacement():
    class FakeWebSocket:
        async def close(self, code: int):
            pass

    async def unregister_old_connection():
        registry = NodeConnectionRegistry()
        old_websocket = FakeWebSocket()
        new_websocket = FakeWebSocket()

        await registry.register("PC-Umar", old_websocket)
        await registry.register("PC-Umar", new_websocket)
        await registry.unregister("PC-Umar", old_websocket)

        return registry, new_websocket

    registry, new_websocket = asyncio.run(
        unregister_old_connection(),
    )

    assert registry.get("PC-Umar") is new_websocket
