import pytest

import venus_node.commands.launcher as launcher

from venus_node.config import NodeSettings
from venus_node.commands.launcher import launch_configured_spotify, launch_spotify


def test_launch_spotify_passes_target_to_windows_launcher():
    launched_targets: list[str] = []

    launch_spotify(
        spotify_target="spotify:",
        start_target=launched_targets.append,
    )

    assert launched_targets == ["spotify:"]


def test_start_windows_target_passes_target_to_os_startfile(monkeypatch):
    called_targets: list[str] = []

    monkeypatch.setattr(
        launcher.os,
        "startfile",
        called_targets.append,
    )

    launcher.start_windows_target("spotify:")

    assert called_targets == ["spotify:"]


def test_start_windows_target_windows_failure_is_not_hidden(monkeypatch):
    def failing_startfile(target: str) -> None:
        raise OSError("Windows failure")

    monkeypatch.setattr(
        launcher.os,
        "startfile",
        failing_startfile,
    )

    with pytest.raises(OSError, match="Windows failure"):
        launcher.start_windows_target("spotify:")


def test_launch_configured_spotify_uses_validated_private_target():
    settings = NodeSettings(
        device_id="laptop-1",
        spotify_target="spotify:",
        core_dev_token="test-node-token",
        core_url="ws://core.test/nodes/connect",
    )
    launched_targets: list[str] = []

    launch_configured_spotify(
        settings=settings,
        start_target=launched_targets.append,
    )

    assert launched_targets == ["spotify:"]
