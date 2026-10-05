import winreg
from pathlib import Path
from uuid import uuid4

import pytest

from venus_node.app import autostart


@pytest.fixture
def run_key():
    # A throwaway key, so tests never touch the real login list.
    key = rf"Software\VenusTest-{uuid4().hex}"
    yield key
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
    except FileNotFoundError:
        pass


def read_value(key: str) -> str:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as run:
        return winreg.QueryValueEx(run, autostart.NAME)[0]


def test_launch_command_quotes_paths_with_spaces():
    command = autostart.launch_command(Path("C:/My Venus/pythonw.exe"), Path("C:/My Venus/venus.pyw"))

    assert command == f'"{Path("C:/My Venus/pythonw.exe")}" "{Path("C:/My Venus/venus.pyw")}"'


def test_enable_writes_the_command_and_disable_removes_it(run_key):
    assert autostart.is_enabled(run_key) is False

    autostart.enable('"pythonw.exe" "venus.pyw"', run_key)

    assert autostart.is_enabled(run_key) is True
    assert read_value(run_key) == '"pythonw.exe" "venus.pyw"'

    autostart.disable(run_key)

    assert autostart.is_enabled(run_key) is False


def test_disable_when_already_off_is_fine(run_key):
    autostart.disable(run_key)

    assert autostart.is_enabled(run_key) is False
