from pathlib import Path

import pytest

# The registry exists only on Windows; Linux runs test_autostart_linux.py.
winreg = pytest.importorskip("winreg")

from venus_node.app import autostart_windows as autostart  # noqa: E402


def read_value(key: str):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as run:
        return winreg.QueryValueEx(run, autostart.NAME)[0]


def write_switch(run_key: str, value: bytes) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, autostart.approved_key(run_key)) as approved:
        winreg.SetValueEx(approved, autostart.NAME, 0, winreg.REG_BINARY, value)


def test_launch_command_quotes_paths_with_spaces():
    command = autostart.launch_command(Path("C:/My Venus/pythonw.exe"), Path("C:/My Venus/venus.pyw"))

    assert command == f'"{Path("C:/My Venus/pythonw.exe")}" "{Path("C:/My Venus/venus.pyw")}"'


def test_enable_writes_the_command_and_disable_removes_it(run_key):
    assert autostart.is_enabled(run_key) is False

    autostart.enable('"pythonw.exe" "venus.pyw"', run_key)

    assert autostart.is_enabled(run_key) is True
    assert read_value(run_key) == '"pythonw.exe" "venus.pyw"'
    assert read_value(autostart.approved_key(run_key)) == autostart.ENABLED

    autostart.disable(run_key)

    assert autostart.is_enabled(run_key) is False


def test_disable_when_already_off_is_fine(run_key):
    autostart.disable(run_key)

    assert autostart.is_enabled(run_key) is False


def test_real_run_key_uses_the_task_manager_switch_list():
    assert autostart.approved_key(autostart.RUN_KEY) == autostart.APPROVED_KEY


def test_command_without_switch_counts_as_off(run_key):
    # Windows 11 skipped exactly this at login (S28).
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, run_key) as run:
        winreg.SetValueEx(run, autostart.NAME, 0, winreg.REG_SZ, "x")

    assert autostart.is_enabled(run_key) is False


def test_approve_missing_fixes_an_old_entry(run_key):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, run_key) as run:
        winreg.SetValueEx(run, autostart.NAME, 0, winreg.REG_SZ, "x")

    autostart.approve_missing(run_key)

    assert autostart.is_enabled(run_key) is True


def test_approve_missing_keeps_a_task_manager_disable(run_key):
    autostart.enable("x", run_key)
    write_switch(run_key, bytes([3] + [0] * 11))

    autostart.approve_missing(run_key)

    assert autostart.is_enabled(run_key) is False


def test_approve_missing_does_nothing_when_off(run_key):
    autostart.approve_missing(run_key)

    assert autostart.read(autostart.approved_key(run_key)) is None
