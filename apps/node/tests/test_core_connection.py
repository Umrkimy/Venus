import asyncio
import pytest

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
    confirmed_device_ids: list[str] = []
    connection_arguments = {}

    def record_connection(hello: NodeHello) -> None:
        confirmed_device_ids.append(hello.device_id)

    class FakeWebSocket:
        def __init__(self):
            self.wait_closed_called = False

        async def send(self, message: str):
            sent_messages.append(message)

        async def recv(self) -> str:
            return NodeHello(device_id="laptop-1").model_dump_json()

        async def wait_closed(self) -> None:
            self.wait_closed_called = True

    class FakeConnection:
        def __init__(self):
            self.websocket = FakeWebSocket()

        async def __aenter__(self):
            return self.websocket

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    fake_connection = FakeConnection()

    def fake_connect(url: str, additional_headers: dict[str, str]):
        connection_arguments["url"] = url
        connection_arguments["headers"] = additional_headers
        return fake_connection

    monkeypatch.setattr(core_connection, "connect", fake_connect)

    confirmed_hello = asyncio.run(
        core_connection.connect_to_core(
            settings,
            on_connected=record_connection,
        ),
    )

    assert connection_arguments == {
        "url": "ws://core.test/nodes/connect",
        "headers": {"Authorization": "Bearer test-node-token"},
    }
    assert NodeHello.model_validate_json(sent_messages[0]).device_id == "laptop-1"
    assert confirmed_hello.device_id == "laptop-1"
    assert confirmed_device_ids == ["laptop-1"]
    assert fake_connection.websocket.wait_closed_called is True


def test_keep_connected_retries_after_network_failure(monkeypatch):
    settings = NodeSettings(
        device_id="laptop-1",
        spotify_target="spotify:",
        core_dev_token="test-node-token",
        core_url="ws://core.test/nodes/connect",
    )
    connection_attempts: list[NodeSettings] = []
    retry_delays: list[int] = []
    retry_notifications: list[bool] = []

    def record_retry() -> None:
        retry_notifications.append(True)

    async def fake_connect_to_core(
        received_settings: NodeSettings,
        on_connected=None,
    ) -> NodeHello:
        connection_attempts.append(received_settings)

        if len(connection_attempts) == 1:
            raise OSError("Core is unavailable")

        raise asyncio.CancelledError

    async def fake_sleep(delay: int) -> None:
        retry_delays.append(delay)

    monkeypatch.setattr(
        core_connection,
        "connect_to_core",
        fake_connect_to_core,
    )
    monkeypatch.setattr(core_connection.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            core_connection.keep_connected(
                settings,
                on_retry=record_retry,
            ),
        )

    assert connection_attempts == [settings, settings]
    assert retry_delays == [1]
    assert retry_notifications == [True]


def test_keep_connected_retries_after_core_disconnect(monkeypatch):
    settings = NodeSettings(
        device_id="laptop-1",
        spotify_target="spotify:",
        core_dev_token="test-node-token",
        core_url="ws://core.test/nodes/connect",
    )
    connection_attempts: list[NodeSettings] = []
    retry_delays: list[int] = []
    retry_notifications: list[bool] = []

    def record_retry() -> None:
        retry_notifications.append(True)

    async def fake_connect_to_core(
        received_settings: NodeSettings,
        on_connected=None,
    ) -> NodeHello:
        connection_attempts.append(received_settings)

        if len(connection_attempts) == 1:
            return NodeHello(device_id=received_settings.device_id)

        raise asyncio.CancelledError

    async def fake_sleep(delay: int) -> None:
        retry_delays.append(delay)

    monkeypatch.setattr(
        core_connection,
        "connect_to_core",
        fake_connect_to_core,
    )
    monkeypatch.setattr(core_connection.asyncio, "sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            core_connection.keep_connected(
                settings,
                on_retry=record_retry,
            ),
        )

    assert connection_attempts == [settings, settings]
    assert retry_delays == [1]
    assert retry_notifications == []
