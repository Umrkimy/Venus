import pytest
from pydantic import ValidationError
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from schemas.commands import OpenApplicationCommand


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


def test_open_application_command_rejects_invalid_application_id():
    with pytest.raises(ValidationError):
        OpenApplicationCommand(
            command_id=uuid4(),
            device_id="laptop-1",
            application_id="brave",
            expires_at=datetime.now(ZoneInfo("Asia/Kuala_Lumpur")) + timedelta(minutes=5),
        )
