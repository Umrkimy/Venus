import venus_node.dev_connect as dev_connect


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

    async def fake_keep_connected(
        settings,
        on_connected=None,
        on_retry=None,
    ) -> None:
        received_settings.append(settings)
        received_callbacks.append((on_connected, on_retry))

    monkeypatch.setattr(
        dev_connect,
        "keep_connected",
        fake_keep_connected,
    )

    dev_connect.run_connect(env_file)

    assert received_settings[0].core_url == "ws://core.test/nodes/connect"
    assert received_callbacks == [
        (dev_connect.print_connected, dev_connect.print_retry),
    ]
