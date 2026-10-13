import sys
import threading
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Linux lock files and sockets")

if sys.platform != "win32":
    from venus_node.app import single_linux


@pytest.fixture(autouse=True)
def own_runtime_dir(tmp_path, monkeypatch):
    # Unix socket paths are short (about 100 characters): keep the folder short too.
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))


def test_claim_lets_only_the_first_holder_run():
    name = rf"Local\VenusTest-{uuid4().hex[:8]}"

    assert single_linux.claim(name) is True
    assert single_linux.claim(name) is False


def test_lock_file_has_no_backslash_name(tmp_path):
    single_linux.claim("Local\\VenusThing")

    assert (tmp_path / "VenusThing.lock").exists()


def test_ask_to_quit_reaches_the_running_app():
    name = rf"Local\VenusQuit-{uuid4().hex[:8]}"
    assert single_linux.ask_to_quit(name) is False  # Nothing running yet.

    server = single_linux.quit_signal(name)
    waiter = threading.Thread(target=single_linux.wait_for_quit, args=(server,))
    waiter.start()

    assert single_linux.ask_to_quit(name) is True
    waiter.join(timeout=5)
    assert not waiter.is_alive()


def test_a_crashed_runs_socket_is_replaced():
    name = rf"Local\VenusStale-{uuid4().hex[:8]}"
    path = single_linux.file_for(name, ".sock")
    path.write_text("left over")

    single_linux.quit_signal(name)

    assert single_linux.ask_to_quit(name) is True
