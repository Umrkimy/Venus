from pathlib import Path

import pytest

from venus_node.commands.desktop_apps import (
    application_dirs,
    exec_command,
    launch_desktop_app,
    read_desktop_apps,
)
from venus_node.commands.start_apps import StartApp

FIREFOX = """[Desktop Entry]
Type=Application
Name=Firefox
Name[de]=Firefox Webbrowser
Exec=/usr/lib/firefox/firefox %u
"""


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_application_dirs_put_your_own_folder_first():
    dirs = application_dirs({"XDG_DATA_HOME": "/home/me/.local/share", "XDG_DATA_DIRS": "/usr/share:/opt/share"})

    assert dirs[:3] == [
        Path("/home/me/.local/share/applications"),
        Path("/usr/share/applications"),
        Path("/opt/share/applications"),
    ]
    # Flatpak apps too, even when XDG_DATA_DIRS doesn't list them.
    assert Path("/var/lib/flatpak/exports/share/applications") in dirs


def test_read_desktop_apps_lists_menu_apps_by_name(tmp_path: Path):
    write(tmp_path, "firefox.desktop", FIREFOX)
    write(tmp_path, "kde4/okular.desktop", "[Desktop Entry]\nType=Application\nName=Okular\nExec=okular %U\n")

    assert read_desktop_apps([tmp_path]) == [
        StartApp(name="Firefox", app_id="firefox.desktop"),
        # Subfolders become part of the id, like the menus do it.
        StartApp(name="Okular", app_id="kde4-okular.desktop"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "[Desktop Entry]\nType=Application\nName=Helper\nExec=helper\nNoDisplay=true\n",
        "[Desktop Entry]\nType=Application\nName=Gone\nExec=gone\nHidden=true\n",
        "[Desktop Entry]\nType=Link\nName=Website\nURL=https://example.com\n",
        "[Desktop Entry]\nType=Application\nName=No command\n",
        "not a desktop file at all",
        "[Desktop Entry]\nName=Broken\n[Desktop Entry]\nName=Twice\n=",
    ],
)
def test_read_desktop_apps_skips_hidden_and_broken_entries(tmp_path: Path, text: str):
    write(tmp_path, "thing.desktop", text)

    assert read_desktop_apps([tmp_path]) == []


def test_your_own_file_beats_the_system_one(tmp_path: Path):
    mine, system = tmp_path / "mine", tmp_path / "system"
    write(system, "firefox.desktop", FIREFOX)
    write(mine, "firefox.desktop", FIREFOX.replace("Name=Firefox", "Name=My Firefox"))

    assert read_desktop_apps([mine, system]) == [StartApp(name="My Firefox", app_id="firefox.desktop")]


def test_hiding_an_app_in_your_folder_hides_the_system_one(tmp_path: Path):
    mine, system = tmp_path / "mine", tmp_path / "system"
    write(system, "firefox.desktop", FIREFOX)
    write(mine, "firefox.desktop", FIREFOX + "Hidden=true\n")

    assert read_desktop_apps([mine, system]) == []


def test_missing_folders_are_fine(tmp_path: Path):
    assert read_desktop_apps([tmp_path / "nope"]) == []


def test_exec_command_drops_file_placeholders_and_keeps_quotes():
    assert exec_command('"/opt/My App/app" --new-window %U --title "100%% done"') == [
        "/opt/My App/app",
        "--new-window",
        "--title",
        "100% done",
    ]


def fake_popen(calls: list):
    def popen(command, **options):
        calls.append((command, options))

    return popen


def test_launch_uses_gio_when_there(tmp_path: Path):
    path = write(tmp_path, "firefox.desktop", FIREFOX)
    calls: list = []

    launch_desktop_app("firefox.desktop", [tmp_path], which=lambda name: "/usr/bin/gio", popen=fake_popen(calls))

    command, options = calls[0]
    assert command == ["/usr/bin/gio", "launch", str(path)]
    # Its own session: quitting Venus never closes the app.
    assert options["start_new_session"] is True


def test_launch_without_gio_runs_the_exec_line_as_a_list(tmp_path: Path):
    write(tmp_path, "evil.desktop", "[Desktop Entry]\nType=Application\nName=Evil\nExec=app; rm -rf ~\n")
    calls: list = []

    launch_desktop_app("evil.desktop", [tmp_path], which=lambda name: None, popen=fake_popen(calls))

    # No shell: ";" and "rm" are just words passed to "app;", never run.
    assert calls[0][0] == ["app;", "rm", "-rf", "~"]


def test_launch_refuses_unknown_or_hidden_apps(tmp_path: Path):
    write(tmp_path, "helper.desktop", "[Desktop Entry]\nType=Application\nName=H\nExec=h\nNoDisplay=true\n")
    calls: list = []

    for app_id in ("nope.desktop", "helper.desktop"):
        with pytest.raises(FileNotFoundError):
            launch_desktop_app(app_id, [tmp_path], which=lambda name: None, popen=fake_popen(calls))
    assert calls == []
