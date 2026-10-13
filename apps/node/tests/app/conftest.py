import sys
from uuid import uuid4

import pytest


@pytest.fixture
def run_key(tmp_path):
    """A throwaway autostart entry, so tests never touch the real login list."""
    if sys.platform == "darwin":
        # Mac: a LaunchAgent .plist in a temp folder.
        yield str(tmp_path / "LaunchAgents" / "dev.venus.node.plist")
        return
    if sys.platform != "win32":
        # Linux: an autostart .desktop file in a temp folder.
        yield str(tmp_path / "autostart" / "venus.desktop")
        return

    import winreg

    from venus_node.app import autostart_windows

    key = rf"Software\VenusTest-{uuid4().hex}"
    yield key
    # The switch subkey first: Windows only deletes keys with no subkeys.
    for each in (autostart_windows.approved_key(key), key):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, each)
        except FileNotFoundError:
            pass
