"""Start Venus at login. Same names on Windows (Run key), Mac (LaunchAgent) and Linux (autostart file).

`key` is where the entry lives: a registry key on Windows, a .desktop file
path on Linux, a LaunchAgent .plist path on a Mac. Tests pass a throwaway one so the real list is never touched.
"""

import sys

if sys.platform == "win32":
    from venus_node.app.autostart_windows import (
        DEFAULT_KEY,
        LABEL,
        approve_missing,
        background_python,
        disable,
        enable,
        is_enabled,
        launch_command,
    )
elif sys.platform == "darwin":
    from venus_node.app.autostart_mac import (
        DEFAULT_KEY,
        LABEL,
        approve_missing,
        background_python,
        disable,
        enable,
        is_enabled,
        launch_command,
    )
else:
    from venus_node.app.autostart_linux import (
        DEFAULT_KEY,
        LABEL,
        approve_missing,
        background_python,
        disable,
        enable,
        is_enabled,
        launch_command,
    )

__all__ = [
    "DEFAULT_KEY",
    "LABEL",
    "approve_missing",
    "background_python",
    "disable",
    "enable",
    "is_enabled",
    "launch_command",
]
