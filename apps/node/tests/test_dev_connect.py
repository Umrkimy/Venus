import venus_node.dev_connect as dev_connect

from venus_protocol.schemas.connections import NodeHello


def test_run_connect_uses_private_settings(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_SPOTIFY_TARGET=spotify:\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
    )
    received_settings = []

    async def fake_connect_to_core(
        settings,
        on_connected=None,
    ):
        received_settings.append(settings)
        return NodeHello(device_id=settings.device_id)

    monkeypatch.setattr(
        dev_connect,
        "connect_to_core",
        fake_connect_to_core,
    )

    confirmed_hello = dev_connect.run_connect(env_file)

    assert confirmed_hello.device_id == "laptop-1"
    assert received_settings[0].core_url == "ws://core.test/nodes/connect"