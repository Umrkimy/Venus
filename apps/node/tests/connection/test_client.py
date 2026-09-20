import json
import asyncio
import pytest

from uuid import uuid4

import venus_node.connection.client as core_connection
import venus_node.connection.messages as messages

from venus_node.config import NodeSettings
from venus_protocol.schemas.commands import CommandResult
from venus_protocol.schemas.connections import NodeHello
from websockets.exceptions import ConnectionClosedError


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
        execute_payload=None,
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


def test_keep_connected_retries_after_abnormal_disconnect(monkeypatch):
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
        execute_payload=None,
    ) -> NodeHello:
        connection_attempts.append(received_settings)

        if len(connection_attempts) == 1:
            raise ConnectionClosedError(None, None)

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
        execute_payload=None,
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


def test_execute_command_message_passes_json_to_executor():
    command_id = uuid4()
    received_payloads: list[dict[str, object]] = []
    expected_result = CommandResult(
        command_id=command_id,
        status="succeeded",
    )

    def fake_execute_payload(
        payload: dict[str, object],
    ) -> CommandResult:
        received_payloads.append(payload)
        return expected_result

    result = messages.execute_command_message(
        json.dumps({"command_id": str(command_id)}),
        fake_execute_payload,
    )

    assert result is expected_result
    assert received_payloads == [
        {"command_id": str(command_id)},
    ]


def test_execute_command_message_discards_malformed_json():
    executor_was_called = False

    def fake_execute_payload(
        payload: dict[str, object],
    ) -> CommandResult:
        nonlocal executor_was_called
        executor_was_called = True
        raise AssertionError("Executor should not receive malformed JSON")

    result = messages.execute_command_message(
        "{not-valid-json}",
        fake_execute_payload,
    )

    assert result is None
    assert executor_was_called is False


def test_receive_and_execute_command_sends_result():
    command_id = uuid4()
    sent_messages: list[str] = []
    expected_result = CommandResult(
        command_id=command_id,
        status="succeeded",
        detail="Fake command completed",
    )

    class FakeWebSocket:
        async def recv(self) -> str:
            return json.dumps({"command_id": str(command_id)})

        async def send(self, message: str) -> None:
            sent_messages.append(message)

    def fake_execute_payload(
        payload: dict[str, object],
    ) -> CommandResult:
        return expected_result

    result = asyncio.run(
        messages.receive_and_execute_command(
            FakeWebSocket(),
            fake_execute_payload,
        ),
    )

    assert result is expected_result
    assert sent_messages == [expected_result.model_dump_json()]


def test_connect_to_core_executes_received_command(monkeypatch):
    settings = NodeSettings(
        device_id="laptop-1",
        spotify_target="spotify:",
        core_dev_token="test-node-token",
        core_url="ws://core.test/nodes/connect",
    )
    command_id = uuid4()
    sent_messages: list[str] = []
    received_payloads: list[dict[str, object]] = []
    expected_result = CommandResult(
        command_id=command_id,
        status="succeeded",
        detail="Fake command completed",
    )

    class FakeWebSocket:
        def __init__(self):
            self.messages = [
                NodeHello(device_id="laptop-1").model_dump_json(),
                json.dumps({"command_id": str(command_id)}),
            ]

        async def send(self, message: str) -> None:
            sent_messages.append(message)

        async def recv(self) -> str:
            return self.messages.pop(0)

    class FakeConnection:
        async def __aenter__(self):
            return FakeWebSocket()

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    def fake_connect(url: str, additional_headers: dict[str, str]):
        return FakeConnection()

    def fake_execute_payload(
        payload: dict[str, object],
    ) -> CommandResult:
        received_payloads.append(payload)
        return expected_result

    monkeypatch.setattr(core_connection, "connect", fake_connect)

    confirmed_hello = asyncio.run(
        core_connection.connect_to_core(
            settings,
            execute_payload=fake_execute_payload,
        ),
    )

    assert confirmed_hello.device_id == "laptop-1"
    assert received_payloads == [{"command_id": str(command_id)}]
    assert sent_messages[1] == expected_result.model_dump_json()
