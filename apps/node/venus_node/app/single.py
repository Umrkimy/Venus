"""One Venus at a time, and a clean Quit from another process.

Windows uses named mutexes and events; Linux uses lock files and a socket.
"""

import sys

if sys.platform == "win32":
    from venus_node.app.single_windows import (
        CONNECTION,
        LISTENER,
        QUIT,
        already_running_message,
        ask_to_quit,
        claim,
        quit_signal,
        wait_for_quit,
    )
else:
    from venus_node.app.single_linux import (
        CONNECTION,
        LISTENER,
        QUIT,
        already_running_message,
        ask_to_quit,
        claim,
        quit_signal,
        wait_for_quit,
    )

__all__ = [
    "CONNECTION",
    "LISTENER",
    "QUIT",
    "already_running_message",
    "ask_to_quit",
    "claim",
    "quit_signal",
    "wait_for_quit",
]
