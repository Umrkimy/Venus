from pathlib import Path

import pytest

from venus_node.commands import launcher, pc


@pytest.fixture
def linux(monkeypatch):
    """Pretend this is Linux and record what would be started."""
    calls = []
    monkeypatch.setattr(pc, "IS_WINDOWS", False)
    monkeypatch.setattr(pc, "IS_MAC", False)
    monkeypatch.setattr(pc.shutil, "which", lambda name: f"/usr/bin/{name}" if name != "code" else None)
    monkeypatch.setattr(pc.subprocess, "Popen", lambda command, **options: calls.append((command, options)))
    return calls


def test_open_link_on_linux_uses_xdg_open(linux):
    pc.open_link("https://www.youtube.com/")

    command, options = linux[0]
    assert command == ["/usr/bin/xdg-open", "https://www.youtube.com/"]
    assert options["start_new_session"] is True


def test_open_folder_on_linux_finds_code_oss(linux):
    # Arch's own VS Code build is called code-oss; plain "code" is missing here.
    pc.open_folder(Path("/home/me/projects/venus"))

    assert linux[0][0] == ["/usr/bin/code-oss", str(Path("/home/me/projects/venus"))]


def test_open_folder_on_linux_without_an_editor_fails_loudly(monkeypatch, linux):
    monkeypatch.setattr(pc.shutil, "which", lambda name: None)

    with pytest.raises(FileNotFoundError, match="VS Code not found"):
        pc.open_folder(Path("/tmp/x"))


def test_launch_app_on_windows_goes_through_the_apps_folder(monkeypatch):
    started = []
    monkeypatch.setattr(pc, "IS_WINDOWS", True)
    monkeypatch.setattr(launcher, "start_windows_target", started.append)

    pc.launch_app("notepad-id")

    assert started == ["shell:AppsFolder\\notepad-id"]


def test_open_link_on_windows_uses_the_default_browser(monkeypatch):
    started = []
    monkeypatch.setattr(pc, "IS_WINDOWS", True)
    monkeypatch.setattr(launcher, "start_windows_target", started.append)

    pc.open_link("https://example.com/")

    assert started == ["https://example.com/"]
