from datetime import datetime, timedelta, timezone

from uuid import uuid4
import pytest

from venus_protocol.schemas.commands import OpenApplicationCommand, OpenUrlCommand

import venus_node.commands.launcher as launcher

from venus_node.config import NodeSettings
from venus_node.commands.start_apps import StartApp


NOTEPAD = StartApp(name="Notepad", app_id="Microsoft.WindowsNotepad_8wekyb3d8bbwe!App")


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


def make_settings() -> NodeSettings:
    return NodeSettings(
        device_id="laptop-1",
        core_dev_token="test-node-token",
        core_url="ws://core.test/nodes/connect",
    )


def make_command(application_id: str) -> OpenApplicationCommand:
    return OpenApplicationCommand(
        command_id=uuid4(),
        device_id="laptop-1",
        application_id=application_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )


def test_application_executor_launches_listed_app():
    started_targets: list[str] = []
    executor = launcher.create_application_command_executor(
        settings=make_settings(),
        start_target=started_targets.append,
        list_apps=lambda: [NOTEPAD],
    )

    result = executor(make_command(NOTEPAD.app_id))

    assert result.status == "succeeded"
    assert started_targets == [f"shell:AppsFolder\\{NOTEPAD.app_id}"]


def test_application_executor_denies_unlisted_app():
    started_targets: list[str] = []
    executor = launcher.create_application_command_executor(
        settings=make_settings(),
        start_target=started_targets.append,
        list_apps=lambda: [NOTEPAD],
    )

    result = executor(make_command("steam://rungameid/1245620"))

    assert result.status == "denied"
    assert result.detail == "Not in this PC's Start menu"
    assert started_targets == []


def make_url_command(url: str) -> OpenUrlCommand:
    return OpenUrlCommand(
        command_id=uuid4(),
        device_id="laptop-1",
        url=url,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )


def test_url_executor_opens_url_in_default_browser():
    started_targets: list[str] = []
    executor = launcher.create_url_command_executor(start_target=started_targets.append)

    result = executor(make_url_command("https://www.youtube.com"))

    assert result.status == "succeeded"
    assert started_targets == ["https://www.youtube.com/"]


def test_command_router_sends_url_command_to_url_executor():
    calls: list[str] = []
    router = launcher.create_command_router(
        open_app=lambda command: calls.append("app"),
        open_url=lambda command: calls.append("url"),
    )

    router(make_url_command("https://www.youtube.com"))

    assert calls == ["url"]
