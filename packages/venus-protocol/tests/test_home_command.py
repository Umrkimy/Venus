from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from venus_protocol.schemas.commands import HomeCommand, node_command_adapter

TUYA = {"address": "192.168.1.40", "tuya_id": "bf1234567890abcdef", "local_key": "k3y!local"}


def home(**fields) -> HomeCommand:
    return HomeCommand(
        command_id=uuid4(),
        device_id="pc-home",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        **fields,
    )


def test_light_brightness_and_color():
    assert home(device="light", action="brightness", value=30, **TUYA).value == 30
    assert home(device="light", action="color", color="#ff0000", **TUYA).color == "#ff0000"


def test_tv_volume_and_wake_and_this_pc():
    assert home(device="tv", action="volume_set", value=20, address="192.168.1.50").value == 20
    assert home(device="wake", action="wake", mac="AA:BB:CC:DD:EE:FF").mac == "AA:BB:CC:DD:EE:FF"
    assert home(device="pc", action="lock").action == "lock"


def test_a_home_payload_parses_as_a_home_command():
    command = home(device="plug", action="off", **TUYA)

    parsed = node_command_adapter.validate_python(command.model_dump(mode="json"))

    assert isinstance(parsed, HomeCommand)


@pytest.mark.parametrize(
    "fields",
    [
        {"device": "plug", "action": "brightness", "value": 10, **TUYA},  # plugs only switch
        {"device": "tv", "action": "lock", "address": "192.168.1.50"},  # not a TV action
        {"device": "light", "action": "brightness", **TUYA},  # no value
        {"device": "light", "action": "brightness", "value": 101, **TUYA},  # over 100
        {"device": "light", "action": "color", "color": "red", **TUYA},  # not #rrggbb
        {"device": "light", "action": "on", "address": "192.168.1.40"},  # no Tuya id or key
        {"device": "tv", "action": "mute"},  # no address
        {"device": "wake", "action": "wake", "mac": "not-a-mac"},
    ],
)
def test_commands_that_dont_fit_the_device_are_refused(fields):
    with pytest.raises(ValidationError):
        home(**fields)


@pytest.mark.parametrize("address", ["8.8.8.8", "127.0.0.1", "example.com", "192.168.1.40; rm -rf /"])
def test_only_home_network_addresses(address):
    # A Venus that can be pointed at internet hosts would be a tool for attacks.
    with pytest.raises(ValidationError):
        home(device="tv", action="mute", address=address)
