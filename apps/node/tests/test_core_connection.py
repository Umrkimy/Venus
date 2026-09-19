import asyncio

import venus_node.core_connection as core_connection

from venus_node.config import NodeSettings
from venus_protocol.schemas.connections import NodeHello


def test_connect_to_core_sends_authenticated_hello(monkeypatch):
    settings = NodeSettings(
        device_id="laptop-1",
        spotify_target="spotify:",
        core_dev_token="test-node-token",
        core_url="ws://core.test/nodes/connect",
    )
    sent_messages: list[str] = []
    connection_arguments = {}

    class FakeWebSocket:
        async def send(self, message: str):
            sent_messages.append(message)

        async def recv(self) -> str:
            return NodeHello(device_id="laptop-1").model_dump_json()

    class FakeConnection:
        async def __aenter__(self):
            return FakeWebSocket()

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    def fake_connect(url: str, additional_headers: dict[str, str]):
        connection_arguments["url"] = url
        connection_arguments["headers"] = additional_headers
        return FakeConnection()

    monkeypatch.setattr(core_connection, "connect", fake_connect)

    confirmed_hello = asyncio.run(
        core_connection.connect_to_core(settings),
    )

    assert connection_arguments == {
        "url": "ws://core.test/nodes/connect",
        "headers": {"Authorization": "Bearer test-node-token"},
    }
    assert NodeHello.model_validate_json(sent_messages[0]).device_id == "laptop-1"
    assert confirmed_hello.device_id == "laptop-1"