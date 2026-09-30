import pytest
from pydantic import ValidationError
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from venus_protocol.schemas.commands import (
    CommandResult,
    OpenApplicationCommand,
    OpenProjectCommand,
    OpenUrlCommand,
    node_command_adapter,
)


def test_open_application_command_accepts_spotify():
    command = OpenApplicationCommand(
        command_id=uuid4(),
        device_id="laptop-1",
        application_id="spotify",
        expires_at=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(minutes=5),
    )

    assert command.application_id == "spotify"


def test_open_application_command_rejects_expired_time():
    with pytest.raises(ValidationError):
        OpenApplicationCommand(
            command_id=uuid4(),
            device_id="laptop-1",
            application_id="spotify",
            expires_at=datetime.now(
                ZoneInfo("Asia/Kuala_Lumpur")
            ) - timedelta(minutes=1),
        )


def test_open_application_command_rejects_naive_time():
    with pytest.raises(ValidationError):
        OpenApplicationCommand(
            command_id=uuid4(),
            device_id="laptop-1",
            application_id="spotify",
            expires_at=datetime.now() + timedelta(minutes=5),
        )


def test_open_application_command_rejects_blank_application_id():
    with pytest.raises(ValidationError):
        OpenApplicationCommand(
            command_id=uuid4(),
            device_id="laptop-1",
            application_id="   ",
            expires_at=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(minutes=5),
        )


def test_command_result_accepts_succeeded_status():
    result = CommandResult(
        command_id=uuid4(),
        status="succeeded",
        detail="Fake executor accepted Spotify",
    )

    assert result.status == "succeeded"


def test_open_application_command_rejects_unknown_field():
    with pytest.raises(ValidationError):
        OpenApplicationCommand(
            command_id=uuid4(),
            device_id="laptop-1",
            application_id="spotify",
            expires_at=datetime.now(
                ZoneInfo("Asia/Kuala_Lumpur")
            ) + timedelta(minutes=5),
            executable_path="C:/unsafe.exe",
        )


def test_open_application_command_rejects_blank_device_id():
    with pytest.raises(ValidationError):
        OpenApplicationCommand(
            command_id=uuid4(),
            device_id="   ",
            application_id="spotify",
            expires_at=datetime.now(
                ZoneInfo("Asia/Kuala_Lumpur")
            ) + timedelta(minutes=5),
        )


def test_open_url_command_accepts_https_url():
    command = OpenUrlCommand(
        command_id=uuid4(),
        device_id="laptop-1",
        url="https://www.youtube.com",
        expires_at=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(minutes=5),
    )

    assert command.url.scheme == "https"


def test_open_url_command_rejects_file_scheme():
    with pytest.raises(ValidationError):
        OpenUrlCommand(
            command_id=uuid4(),
            device_id="laptop-1",
            url="file:///C:/Windows/System32/cmd.exe",
            expires_at=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(minutes=5),
        )


def test_node_command_picks_model_by_kind():
    command = node_command_adapter.validate_python(
        {
            "kind": "open_url",
            "command_id": str(uuid4()),
            "device_id": "laptop-1",
            "url": "https://www.youtube.com",
            "expires_at": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(minutes=5),
        }
    )

    assert isinstance(command, OpenUrlCommand)


def make_project_command(project_name: str) -> OpenProjectCommand:
    return OpenProjectCommand(
        command_id=uuid4(),
        device_id="laptop-1",
        project_name=project_name,
        expires_at=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(minutes=5),
    )


def test_open_project_command_accepts_folder_name():
    command = make_project_command("Venus")

    assert command.project_name == "Venus"


@pytest.mark.parametrize("project_name", ["a\\b", "a/b", "..", ".", "   "])
def test_open_project_command_rejects_path_like_names(project_name: str):
    with pytest.raises(ValidationError):
        make_project_command(project_name)


def test_node_command_adapter_parses_open_project():
    command = node_command_adapter.validate_python(
        {
            "kind": "open_project",
            "command_id": str(uuid4()),
            "device_id": "laptop-1",
            "project_name": "Venus",
            "expires_at": (
                datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(minutes=5)
            ).isoformat(),
        }
    )

    assert isinstance(command, OpenProjectCommand)
