import threading

from venus_node.config import NodeSettings
from venus_node.voice.reporter import report_loop
from venus_node.voice.status import SPEAKING, Status

SETTINGS = NodeSettings(device_id="pc-umar", core_dev_token="node-token", core_url="ws://core.test:9000/nodes/connect")


def test_reports_state_subtitle_muted_and_learns_web_is_watching():
    status = Status()
    status.set(SPEAKING, "hi babe")
    muted = threading.Event()
    muted.set()
    sent = []

    def send(state: str, subtitle: str, is_muted: bool):
        sent.append((state, subtitle, is_muted))
        status.close()  # One round is enough.
        return True, True, False

    report_loop(SETTINGS, status, muted, send=send, every=0.01)

    assert sent == [("speaking", "hi babe", True)]
    assert status.web_watching is True
    assert status.web_listening is True


def test_web_stop_button_stops_luna():
    status = Status()

    def send(state: str, subtitle: str, is_muted: bool):
        status.close()
        return True, False, True

    report_loop(SETTINGS, status, send=send, every=0.01)

    assert status.stop.is_set()


def test_core_down_means_the_pc_orb_shows():
    status = Status()
    status.set_web_watching(True)

    def send(state: str, subtitle: str, is_muted: bool):
        status.close()
        raise ConnectionRefusedError("Core is down")

    report_loop(SETTINGS, status, send=send, every=0.01)

    assert status.web_watching is False


def test_a_change_is_reported_without_waiting_for_the_next_tick():
    status = Status()
    sent = []
    first = threading.Event()

    def send(state: str, subtitle: str, is_muted: bool):
        sent.append(state)
        first.set()
        if len(sent) == 2:
            status.close()
        return False, False, False

    thread = threading.Thread(target=report_loop, kwargs={"settings": SETTINGS, "status": status, "send": send, "every": 60})
    thread.start()
    first.wait(2)
    status.set(SPEAKING, "hi")
    thread.join(2)

    # A 60 s tick would still be waiting; the change woke it.
    assert not thread.is_alive()
    assert sent == ["idle", "speaking"]
