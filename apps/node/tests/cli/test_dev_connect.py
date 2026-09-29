import venus_node.cli.dev_connect as dev_connect


def test_run_connect_uses_private_settings(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_SPOTIFY_TARGET=spotify:\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
    )
    received_settings = []
    received_callbacks = []

    class FakeExecutor:
        def execute_payload(self, payload):
            return None

    fake_executor = FakeExecutor()

    async def fake_keep_connected(
        settings,
        on_connected=None,
        on_retry=None,
        execute_payload=None,
        list_apps=None,
    ) -> None:
        received_settings.append(settings)
        received_callbacks.append(
            (on_connected, on_retry, execute_payload),
        )

    monkeypatch.setattr(
        dev_connect,
        "keep_connected",
        fake_keep_connected,
    )
    monkeypatch.setattr(
        dev_connect,
        "create_fake_node_executor",
        lambda env_file, database_path: fake_executor,
    )

    dev_connect.run_connect(env_file)

    assert received_settings[0].core_url == "ws://core.test/nodes/connect"
    assert received_callbacks == [
        (
            dev_connect.print_connected,
            dev_connect.print_retry,
            fake_executor.execute_payload,
        ),
    ]


def test_run_connect_uses_real_executor_when_enabled(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_SPOTIFY_TARGET=spotify:\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
        "VENUS_NODE_REAL_ACTIONS=true\n"
    )
    received_payload_handlers = []

    class RealExecutor:
        def execute_payload(self, payload):
            return None

    real_executor = RealExecutor()

    async def fake_keep_connected(settings, on_connected=None, on_retry=None, execute_payload=None, list_apps=None):
        received_payload_handlers.append(execute_payload)

    def fail_fake_factory(env_file, database_path):
        raise AssertionError("fake executor must not be used")

    monkeypatch.setattr(dev_connect, "keep_connected", fake_keep_connected)
    monkeypatch.setattr(dev_connect, "create_node_executor", lambda env_file, database_path: real_executor)
    monkeypatch.setattr(dev_connect, "create_fake_node_executor", fail_fake_factory)

    dev_connect.run_connect(env_file)

    assert received_payload_handlers == [real_executor.execute_payload]


def test_run_connect_uses_fake_executor_by_default(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_SPOTIFY_TARGET=spotify:\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
    )
    received_payload_handlers = []

    class FakeExecutor:
        def execute_payload(self, payload):
            return None

    fake_executor = FakeExecutor()

    async def fake_keep_connected(settings, on_connected=None, on_retry=None, execute_payload=None, list_apps=None):
        received_payload_handlers.append(execute_payload)

    def fail_real_factory(env_file, database_path):
        raise AssertionError("real executor must not be used by default")

    monkeypatch.setattr(dev_connect, "keep_connected", fake_keep_connected)
    monkeypatch.setattr(dev_connect, "create_node_executor", fail_real_factory)
    monkeypatch.setattr(dev_connect, "create_fake_node_executor", lambda env_file, database_path: fake_executor)

    dev_connect.run_connect(env_file)

    assert received_payload_handlers == [fake_executor.execute_payload]