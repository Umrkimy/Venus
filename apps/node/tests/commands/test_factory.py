from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from venus_node.commands import pc

from venus_node.commands.factory import (
    create_fake_node_executor,
    create_node_executor,
)
from venus_node.commands.start_apps import StartApp


def test_create_node_executor_uses_private_settings_and_pc_launcher(
    tmp_path,
    monkeypatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
    )
    database_path = tmp_path / "node.db"
    launched: list[str] = []

    monkeypatch.setattr(pc, "launch_app", launched.append)
    monkeypatch.setattr(
        pc,
        "list_apps",
        lambda: [StartApp(name="Notepad", app_id="notepad-id")],
    )

    executor = create_node_executor(
        env_file=env_file,
        database_path=database_path,
    )

    result = executor.execute_payload(
        {
            "command_id": str(uuid4()),
            "device_id": "laptop-1",
            "application_id": "notepad-id",
            "expires_at": datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
            + timedelta(minutes=5),
        }
    )

    assert result is not None
    assert result.status == "succeeded"
    assert launched == ["notepad-id"]


def test_create_fake_node_executor_does_not_launch_anything(
    tmp_path,
    monkeypatch,
):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "VENUS_NODE_DEVICE_ID=laptop-1\n"
        "VENUS_NODE_CORE_DEV_TOKEN=test-node-token\n"
        "VENUS_NODE_CORE_URL=ws://core.test/nodes/connect\n"
    )
    database_path = tmp_path / "node.db"

    def unexpected_launch(target: str) -> None:
        raise AssertionError("Fake executor must not launch anything")

    monkeypatch.setattr(pc, "launch_app", unexpected_launch)

    executor = create_fake_node_executor(
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
        },
    )

    assert result is not None
    assert result.status == "succeeded"
    assert result.detail == "Fake executor accepted spotify"
