from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from venus_protocol.schemas.commands import HomeCommand

from venus_node.commands import home
from venus_node.commands.launcher import create_command_router

TUYA = {"address": "192.168.1.40", "tuya_id": "bf1234567890abcdef", "local_key": "k3y!local"}


def command(**fields) -> HomeCommand:
    return HomeCommand(
        command_id=uuid4(),
        device_id="pc-home",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        **fields,
    )


class FakeBulb:
    def __init__(self, answer=None):
        self.calls = []
        self.answer = answer or {"dps": {"20": True}}

    def __getattr__(self, name):
        def call(*args):
            self.calls.append((name, *args))
            return self.answer

        return call


@pytest.mark.parametrize(
    ("fields", "calls", "detail"),
    [
        ({"action": "on"}, [("turn_on",)], "On"),
        ({"action": "off"}, [("turn_off",)], "Off"),
        ({"action": "brightness", "value": 30}, [("turn_on",), ("set_brightness_percentage", 30)], "Brightness 30%"),
        ({"action": "brightness", "value": 0}, [("turn_off",)], "Off"),
        ({"action": "color", "color": "#ff8000"}, [("turn_on",), ("set_colour", 255, 128, 0)], "Color #ff8000"),
    ],
)
def test_tuya_light_actions(fields, calls, detail):
    bulb = FakeBulb()

    result = home.run_tuya(command(device="light", **TUYA, **fields), make_device=lambda c: bulb)

    assert bulb.calls == calls
    assert result == detail


def test_tuya_error_answer_becomes_a_clear_failure():
    bulb = FakeBulb(answer={"Error": "Network Error: Device Unreachable", "Err": "905"})
    run = home.create_home_executor(tuya=lambda c: home.run_tuya(c, make_device=lambda _: bulb))

    result = run(command(device="plug", action="on", **TUYA))

    assert result.status == "failed"
    assert "didn't answer" in result.detail


class FakeCast:
    def __init__(self):
        self.calls = []
        self.socket_client = self
        self.receiver_controller = self

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.calls.append((name, *args))


@pytest.mark.parametrize(
    ("fields", "call", "detail"),
    [
        ({"action": "volume_up"}, ("volume_up", 0.1), "Volume up"),
        ({"action": "volume_down"}, ("volume_down", 0.1), "Volume down"),
        ({"action": "volume_set", "value": 25}, ("set_volume", 0.25), "Volume 25"),
        ({"action": "mute"}, ("set_volume_muted", True), "Muted"),
        ({"action": "unmute"}, ("set_volume_muted", False), "Unmuted"),
    ],
)
def test_tv_volume_over_cast(fields, call, detail):
    cast = FakeCast()

    result = home.run_tv(command(device="tv", address="192.168.1.50", **fields), connect=lambda address: cast)

    assert cast.calls == [call, ("disconnect",)]
    assert result == detail


def test_tv_that_cant_be_reached_says_so():
    def offline(address):
        raise OSError("timed out")

    with pytest.raises(home.HomeError, match="Couldn't reach the TV"):
        home.run_tv(command(device="tv", action="mute", address="192.168.1.50"), connect=offline)


def test_magic_packet_is_ff_then_the_mac_16_times():
    packet = home.magic_packet("AA:BB:CC:DD:EE:FF")

    assert packet[:6] == b"\xff" * 6
    assert packet[6:] == bytes.fromhex("aabbccddeeff") * 16
    assert len(packet) == 102


def test_wake_sends_the_packet():
    sent = []

    result = home.run_wake(command(device="wake", action="wake", mac="aa-bb-cc-dd-ee-ff"), send=sent.append)

    assert sent == [home.magic_packet("aa-bb-cc-dd-ee-ff")]
    assert result == "Wake-up sent"


def fake_pc(volume=50):
    state = {"volume": volume, "muted": True, "locked": False}
    pc = home.ThisPc(
        get_volume=lambda: state["volume"],
        set_volume=lambda level: state.update(volume=level),
        set_muted=lambda muted: state.update(muted=muted),
        lock=lambda: state.update(locked=True),
    )
    return pc, state


@pytest.mark.parametrize(
    ("fields", "start", "volume", "detail"),
    [
        ({"action": "volume_up"}, 50, 60, "Volume 60"),
        ({"action": "volume_down"}, 5, 0, "Volume 0"),
        ({"action": "volume_up"}, 95, 100, "Volume 100"),
        ({"action": "volume_set", "value": 35}, 50, 35, "Volume 35"),
    ],
)
def test_this_pc_volume_stays_in_range_and_unmutes(fields, start, volume, detail):
    pc, state = fake_pc(start)

    result = home.run_pc(command(device="pc", **fields), pc=pc)

    assert state["volume"] == volume
    assert state["muted"] is False
    assert result == detail


def test_this_pc_mute_and_lock():
    pc, state = fake_pc()

    home.run_pc(command(device="pc", action="mute"), pc=pc)
    home.run_pc(command(device="pc", action="lock"), pc=pc)

    assert state["muted"] is True
    assert state["locked"] is True


def test_router_sends_home_commands_to_home_and_refuses_without_it():
    seen = []
    def unused(c):
        raise AssertionError("not a home command")

    with_home = create_command_router(unused, unused, unused, home=lambda c: seen.append(c) or "ok")
    without = create_command_router(unused, unused, unused)
    pc_lock = command(device="pc", action="lock")

    assert with_home(pc_lock) == "ok"
    assert without(pc_lock).status == "denied"
