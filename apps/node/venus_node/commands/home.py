"""Home control from the Node: Tuya lights and plugs, the TV over Google Cast,
Wake-on-LAN for another PC, and this PC's own volume and lock.

The Node runs on your PC, inside your home network, so it can reach the
bulbs and the TV directly (Core runs in Docker, which can't send the
network-wide broadcast Wake-on-LAN needs). Each library is imported only
when its device is used, so an unused one costs no RAM.
"""

import shutil
import socket
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field

from venus_protocol.schemas.commands import CommandResult, HomeCommand

from venus_node.commands.pc import IS_WINDOWS

# Steps for "volume up/down": a tenth of the range.
VOLUME_STEP = 10
CAST_PORT = 8009
WAKE_PORTS = (9, 7)


class HomeError(Exception):
    """A device said no or didn't answer; the message is shown in the chat."""


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


# --- Tuya lights and plugs -------------------------------------------------


def tuya_device(command: HomeCommand):
    import tinytuya

    kind = tinytuya.BulbDevice if command.device == "light" else tinytuya.OutletDevice
    device = kind(command.tuya_id, command.address, command.local_key, version=command.tuya_version)
    device.set_socketTimeout(4)
    device.set_socketRetryLimit(1)
    return device


def tuya_checked(answer) -> None:
    # tinytuya answers with {"Error": ...} instead of raising.
    if isinstance(answer, dict) and "Error" in answer:
        raise HomeError(f"The light didn't answer ({answer['Error']})")


def run_tuya(command: HomeCommand, make_device: Callable = tuya_device) -> str:
    device = make_device(command)
    if command.action == "on":
        tuya_checked(device.turn_on())
        return "On"
    if command.action == "off":
        tuya_checked(device.turn_off())
        return "Off"
    if command.action == "brightness":
        if command.value == 0:
            tuya_checked(device.turn_off())
            return "Off"
        tuya_checked(device.turn_on())
        tuya_checked(device.set_brightness_percentage(command.value))
        return f"Brightness {command.value}%"
    tuya_checked(device.turn_on())
    tuya_checked(device.set_colour(*hex_to_rgb(command.color)))
    return f"Color {command.color}"


# --- TV over Google Cast ---------------------------------------------------


def cast_device(address: str):
    # pychromecast takes ~25 s to give up on a TV that's off; a quick knock first.
    socket.create_connection((address, CAST_PORT), timeout=3).close()
    import pychromecast

    cast = pychromecast.get_chromecast_from_host((address, CAST_PORT, None, None, None), tries=1, timeout=5)
    cast.wait(timeout=5)
    return cast


def run_tv(command: HomeCommand, connect: Callable = cast_device) -> str:
    try:
        cast = connect(command.address)
    except Exception as exc:
        raise HomeError("Couldn't reach the TV. Is it on and on the same Wi-Fi?") from exc
    try:
        receiver = cast.socket_client.receiver_controller
        if command.action == "volume_up":
            cast.volume_up(VOLUME_STEP / 100)
        elif command.action == "volume_down":
            cast.volume_down(VOLUME_STEP / 100)
        elif command.action == "volume_set":
            receiver.set_volume(command.value / 100)
        else:
            receiver.set_volume_muted(command.action == "mute")
    finally:
        cast.disconnect(timeout=2)
    return {"volume_up": "Volume up", "volume_down": "Volume down", "mute": "Muted", "unmute": "Unmuted"}.get(
        command.action, f"Volume {command.value}"
    )


# --- Wake-on-LAN -----------------------------------------------------------


def magic_packet(mac: str) -> bytes:
    """Six 0xFF bytes, then the MAC 16 times: what a sleeping network card listens for."""
    raw = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    return b"\xff" * 6 + raw * 16


def send_broadcast(packet: bytes) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for port in WAKE_PORTS:
            sender.sendto(packet, ("255.255.255.255", port))


def run_wake(command: HomeCommand, send: Callable[[bytes], None] = send_broadcast) -> str:
    send(magic_packet(command.mac))
    return "Wake-up sent"


# --- This PC ---------------------------------------------------------------


@dataclass
class ThisPc:
    """This PC's volume (0-100) and lock, swappable in tests."""

    get_volume: Callable[[], int]
    set_volume: Callable[[int], None]
    set_muted: Callable[[bool], None]
    lock: Callable[[], None]
    calls: list = field(default_factory=list)


def windows_pc() -> ThisPc:
    def speakers():
        from pycaw.pycaw import AudioUtilities

        return AudioUtilities.GetSpeakers().EndpointVolume

    def lock() -> None:
        import ctypes

        ctypes.windll.user32.LockWorkStation()

    return ThisPc(
        get_volume=lambda: round(speakers().GetMasterVolumeLevelScalar() * 100),
        set_volume=lambda level: speakers().SetMasterVolumeLevelScalar(level / 100, None),
        set_muted=lambda muted: speakers().SetMute(int(muted), None),
        lock=lock,
    )


def run_quiet(command: list[str]) -> str:
    return subprocess.run(command, capture_output=True, text=True, check=True, timeout=5).stdout


def linux_pc() -> ThisPc:
    # PipeWire (CachyOS, Fedora, new Ubuntu) has wpctl; older setups have pactl.
    wpctl = shutil.which("wpctl")
    sink = "@DEFAULT_AUDIO_SINK@"

    def get_volume() -> int:
        if wpctl:
            # "Volume: 0.45" or "Volume: 0.45 [MUTED]"
            return round(float(run_quiet([wpctl, "get-volume", sink]).split()[1]) * 100)
        out = run_quiet(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        return int(out.split("/")[1].strip().rstrip("%"))

    def set_volume(level: int) -> None:
        if wpctl:
            run_quiet([wpctl, "set-volume", sink, f"{level / 100:.2f}"])
        else:
            run_quiet(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"])

    def set_muted(muted: bool) -> None:
        if wpctl:
            run_quiet([wpctl, "set-mute", sink, "1" if muted else "0"])
        else:
            run_quiet(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if muted else "0"])

    return ThisPc(
        get_volume=get_volume,
        set_volume=set_volume,
        set_muted=set_muted,
        lock=lambda: run_quiet(["loginctl", "lock-session"]) and None,
    )


def run_pc(command: HomeCommand, pc: ThisPc | None = None) -> str:
    pc = pc or (windows_pc() if IS_WINDOWS else linux_pc())
    if command.action == "lock":
        pc.lock()
        return "Locked"
    if command.action in ("mute", "unmute"):
        pc.set_muted(command.action == "mute")
        return "Muted" if command.action == "mute" else "Unmuted"
    if command.action == "volume_set":
        level = command.value
    else:
        step = VOLUME_STEP if command.action == "volume_up" else -VOLUME_STEP
        level = max(0, min(100, pc.get_volume() + step))
    pc.set_volume(level)
    pc.set_muted(False)  # Turning it up while muted would do nothing you can hear.
    return f"Volume {level}"


# --- Router ----------------------------------------------------------------


def create_home_executor(
    tuya: Callable[[HomeCommand], str] = run_tuya,
    tv: Callable[[HomeCommand], str] = run_tv,
    wake: Callable[[HomeCommand], str] = run_wake,
    pc: Callable[[HomeCommand], str] = run_pc,
) -> Callable[[HomeCommand], CommandResult]:
    by_device = {"light": tuya, "plug": tuya, "tv": tv, "wake": wake, "pc": pc}

    def execute(command: HomeCommand) -> CommandResult:
        try:
            detail = by_device[command.device](command)
        except HomeError as exc:
            return CommandResult(command_id=command.command_id, status="failed", detail=str(exc))
        return CommandResult(command_id=command.command_id, status="succeeded", detail=detail)

    return execute
