from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import venus_node.runtime as runtime

from venus_node.runtime import create_node_executor


def test_create_node_executor_uses_private_settings_and_windows_launcher(
    tmp_path,
    monkeypatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_SPOTIFY_TARGET=spotify:\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
    )
    database_path = tmp_path / "node.db"
    started_targets: list[str] = []

    monkeypatch.setattr(
        runtime,
        "start_windows_target",
        started_targets.append,
    )

    executor = create_node_executor(
        env_file=env_file,
        database_path=database_path,
    )

    result = executor.execute_payload(
        {
            "command_id": str(uuid4()),
            "device_id": "laptop-1",
            "application_id": "spotify",
            "expires_at": datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
            + timedelta(minutes=5),
        }
    )

    assert result is not None
    assert result.status == "succeeded"
    assert started_targets == ["spotify:"]
