import winreg
from threading import Event
from uuid import uuid4

import pystray
import pytest

from venus_node.app import autostart
from venus_node.app.tray import GREY, CRIMSON, Tray, status_text


@pytest.fixture
def run_key():
    key = rf"Software\VenusTest-{uuid4().hex}"
    yield key
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key)
    except FileNotFoundError:
        pass


def make_tray(run_key, events=None):
    events = events if events is not None else []
    tray = Tray(
        Event(),
        open_venus=lambda: events.append("open"),
        autostart_command='"pythonw.exe" "venus.pyw"',
        quit=lambda: events.append("quit"),
        autostart_key=run_key,
    )
    return tray, events


def items(tray):
    return [i for i in tray.icon.menu.items if i is not pystray.Menu.SEPARATOR]


def item(tray, text):
    return next(i for i in items(tray) if i.text == text)


def colour(tray):
    return tray.icon.icon.getpixel((32, 32))


def test_status_text_covers_connection_and_mute():
    assert status_text(connected=True, muted=False) == "Connected"
    assert status_text(connected=False, muted=False) == "Core offline"
    assert status_text(connected=True, muted=True) == "Connected, mic muted"


def test_menu_has_status_open_stop_mute_autostart_quit(run_key):
    tray, _ = make_tray(run_key)

    assert [i.text for i in items(tray)] == ["Core offline", "Open Venus", "Stop talking", "Mute mic", "Start with Windows", "Quit"]
    assert items(tray)[0].enabled is False  # Status line is only information.


def test_connecting_updates_status_line_and_turns_icon_crimson(run_key):
    tray, _ = make_tray(run_key)
    assert colour(tray) == GREY

    tray.set_connected(True)

    assert items(tray)[0].text == "Connected"
    assert colour(tray) == CRIMSON


def test_mute_sets_the_event_and_greys_the_icon(run_key):
    tray, _ = make_tray(run_key)
    tray.set_connected(True)

    item(tray, "Mute mic")(tray.icon)

    assert tray.muted.is_set()
    assert item(tray, "Mute mic").checked is True
    assert items(tray)[0].text == "Connected, mic muted"
    assert colour(tray) == GREY

    item(tray, "Mute mic")(tray.icon)

    assert not tray.muted.is_set()
    assert colour(tray) == CRIMSON


def test_web_mute_and_unmute_go_through_set_muted(run_key):
    tray, _ = make_tray(run_key)
    tray.set_connected(True)

    tray.set_muted(True)
    assert tray.muted.is_set()
    assert colour(tray) == GREY

    tray.set_muted(False)
    assert not tray.muted.is_set()
    assert colour(tray) == CRIMSON


def test_start_with_windows_toggles_the_run_entry(run_key):
    tray, _ = make_tray(run_key)
    assert item(tray, "Start with Windows").checked is False

    item(tray, "Start with Windows")(tray.icon)

    assert autostart.is_enabled(run_key)
    assert item(tray, "Start with Windows").checked is True

    item(tray, "Start with Windows")(tray.icon)

    assert not autostart.is_enabled(run_key)


def test_open_venus_and_quit_call_back(run_key):
    tray, events = make_tray(run_key)

    item(tray, "Open Venus")(tray.icon)
    item(tray, "Quit")(tray.icon)

    assert events == ["open", "quit"]



def test_stop_talking_calls_back(run_key):
    stopped = []
    tray = Tray(
        Event(), open_venus=lambda: None, autostart_command="x", quit=lambda: None,
        autostart_key=run_key, stop_talking=lambda: stopped.append(True),
    )

    item(tray, "Stop talking")(tray.icon)

    assert stopped == [True]
