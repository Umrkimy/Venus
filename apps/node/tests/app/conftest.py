import winreg
from uuid import uuid4

import pytest

from venus_node.app import autostart


@pytest.fixture
def run_key():
    # A throwaway key, so tests never touch the real login list.
    key = rf"Software\VenusTest-{uuid4().hex}"
    yield key
    # The switch subkey first: Windows only deletes keys with no subkeys.
    for each in (autostart.approved_key(key), key):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, each)
        except FileNotFoundError:
            pass
