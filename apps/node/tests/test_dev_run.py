from uuid import UUID

import venus_node.dev_run as dev_run

from venus_protocol.schemas.commands import CommandResult


def test_run_spotify_sends_local_spotify_command(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_SPOTIFY_TARGET=spotify:\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
    )
    database_path = tmp_path / "node.db"
    received_payloads = []

    class FakeNodeExecutor:
        def execute_payload(self, payload):
            received_payloads.append(payload)

            return CommandResult(
                command_id=UUID(str(payload["command_id"])),
                status="succeeded",
                detail="Fake Spotify launch",
            )

    monkeypatch.setattr(
        dev_run,
        "create_node_executor",
        lambda env_file, database_path: FakeNodeExecutor(),
    )

    result = dev_run.run_spotify(
        env_file=env_file,
        database_path=database_path,
    )

    assert result.status == "succeeded"
    assert len(received_payloads) == 1
    assert received_payloads[0]["device_id"] == "laptop-1"
    assert received_payloads[0]["application_id"] == "spotify"
    UUID(str(received_payloads[0]["command_id"]))
