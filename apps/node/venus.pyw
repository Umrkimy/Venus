# Venus on this PC with no console window: connection, "Hey Venus", orb, tray icon.
# Run with this folder's Python: .venv\Scripts\pythonw.exe venus.pyw (Windows)
# or .venv/bin/python venus.pyw --hidden (Linux).
# Tray menu: "Start with Windows" / "Start at login". Messages: data/venus-node.log.
import os
import sys

# The tray icon and orb need a desktop. On a Linux PC without one, say so
# instead of failing deep inside the tray library.
if sys.platform != "win32" and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    sys.exit("No desktop found. For actions only, run: .venv/bin/python -m venus_node.dev_connect")

from venus_node.app.main import main  # noqa: E402

main()
