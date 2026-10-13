"""The Mac parts, run on any OS: nothing here starts a real app or touches the volume."""

import plistlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from venus_protocol.schemas.commands import HomeCommand

from venus_node.app import autostart_mac
from venus_node.commands import home, mac_apps, pc


def make_apps(tmp_path: Path) -> list[Path]:
    mine = tmp_path / "home-Applications"
    system = tmp_path / "Applications"
    for folder, names in ((mine, ["Spotify"]), (system, ["Spotify", "Safari", "Visual Studio Code", "notes.txt"])):
        folder.mkdir()
        for name in names:
            (folder / (name if name.endswith(".txt") else f"{name}.app")).mkdir()
    return [mine, system, tmp_path / "missing"]


def test_apps_are_the_app_bundles_and_your_own_copy_wins(tmp_path):
    dirs = make_apps(tmp_path)

    apps = mac_apps.read_mac_apps(dirs)

    assert [app.name for app in apps] == ["Safari", "Spotify", "Visual Studio Code"]
    assert apps[1].app_id == str(dirs[0] / "Spotify.app")


def test_launch_opens_a_listed_app_with_open_a(tmp_path):
    dirs = make_apps(tmp_path)
    calls = []

    mac_apps.launch_mac_app(str(dirs[1] / "Safari.app"), dirs, popen=lambda command, **o: calls.append((command, o)))

    assert calls[0][0] == ["open", "-a", str(dirs[1] / "Safari.app")]
    assert calls[0][1]["start_new_session"] is True


@pytest.mark.parametrize("app_id", ["/bin/sh", "/Applications/../../bin/sh", "Safari"])
def test_launch_refuses_anything_not_in_the_list(tmp_path, app_id):
    with pytest.raises(FileNotFoundError):
        mac_apps.launch_mac_app(app_id, make_apps(tmp_path), popen=lambda *a, **o: pytest.fail("started"))


def test_links_and_folders():
    calls = []
    popen = lambda command, **o: calls.append(command)  # noqa: E731

    mac_apps.open_with_mac("https://www.youtube.com/", popen=popen)
    mac_apps.open_folder_in_code(Path("/Users/me/code/venus"), which=lambda name: "/usr/local/bin/code", popen=popen)
    mac_apps.open_folder_in_code(Path("/Users/me/code/venus"), which=lambda name: None, popen=popen)

    folder = str(Path("/Users/me/code/venus"))
    assert calls == [
        ["open", "https://www.youtube.com/"],
        ["/usr/local/bin/code", folder],
        ["open", "-a", "Visual Studio Code", folder],
    ]


def test_notification_text_is_an_argument_not_code():
    calls = []
    sneaky = 'Class" & do shell script "rm -rf ~'

    mac_apps.notify_mac("Venus reminder", sneaky, run=lambda command, **o: calls.append(command))

    command = calls[0]
    assert command[:2] == ["osascript", "-e"]
    assert sneaky not in command[2]  # The script itself never contains the text.
    assert command[3:] == ["Venus reminder", sneaky]


def test_pc_routes_to_the_mac_versions(monkeypatch):
    calls = []
    monkeypatch.setattr(pc, "IS_WINDOWS", False)
    monkeypatch.setattr(pc, "IS_MAC", True)
    monkeypatch.setattr(mac_apps, "launch_mac_app", lambda app_id: calls.append(("app", app_id)))
    monkeypatch.setattr(mac_apps, "open_with_mac", lambda url: calls.append(("link", url)))
    monkeypatch.setattr(mac_apps, "open_folder_in_code", lambda folder: calls.append(("folder", folder)))
    monkeypatch.setattr(mac_apps, "read_mac_apps", lambda dirs: ["listed"])

    pc.launch_app("/Applications/Safari.app")
    pc.open_link("https://github.com")
    pc.open_folder(Path("/Users/me/x"))

    assert calls == [("app", "/Applications/Safari.app"), ("link", "https://github.com"), ("folder", Path("/Users/me/x"))]
    assert pc.list_apps() == ["listed"]


def test_mac_volume_and_lock_use_osascript_and_pmset():
    calls = []

    def run(command):
        calls.append(command)
        return "45\n" if "get volume settings" in command[-1] else ""

    mac = home.mac_pc(run)
    detail = home.run_pc(home_command("volume_up"), pc=mac)
    home.run_pc(home_command("mute"), pc=mac)
    home.run_pc(home_command("lock"), pc=mac)

    assert detail == "Volume 55"
    assert ["osascript", "-e", "set volume output volume 55"] in calls
    assert ["osascript", "-e", "set volume output muted true"] in calls
    assert calls[-1] == ["pmset", "displaysleepnow"]


def home_command(action: str) -> HomeCommand:
    return HomeCommand(
        command_id=uuid4(),
        device_id="mac-home",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        device="pc",
        action=action,
    )


def test_login_item_is_a_launch_agent(tmp_path):
    key = str(tmp_path / "LaunchAgents" / "dev.venus.node.plist")
    python, launcher = Path("/Users/me/My Venus/.venv/bin/python"), Path("/Users/me/My Venus/venus.pyw")
    command = autostart_mac.launch_command(python, launcher)

    assert not autostart_mac.is_enabled(key)
    autostart_mac.enable(command, key)

    agent = plistlib.loads(Path(key).read_bytes())
    # One word per argument, spaces and all: no shell in between.
    assert agent["ProgramArguments"] == [str(python), str(launcher), "--hidden"]
    assert agent["RunAtLoad"] is True
    assert autostart_mac.is_enabled(key)
    autostart_mac.disable(key)
    assert not autostart_mac.is_enabled(key)
