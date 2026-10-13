from datetime import datetime, timedelta, timezone
from urllib.error import URLError

from venus_node.app import reminders
from venus_node.app.reminders import Reminders, reminder_text

NOW = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)


def event(title="Database class", minutes=8, location="Room 3", event_id="google:d"):
    return {
        "id": event_id,
        "title": title,
        "start": (NOW + timedelta(minutes=minutes)).isoformat(),
        "location": location,
    }


def test_reminder_text_says_what_when_and_where():
    assert reminder_text(event(), NOW) == "Database class in 8 min (Room 3)"
    assert reminder_text(event(minutes=0, location=""), NOW) == "Database class now"


def test_each_event_pops_up_once():
    shown = []
    upcoming = [event()]
    checker = Reminders(fetch=lambda: upcoming, notify=shown.append, clock=lambda: NOW)

    checker.check()
    checker.check()

    assert shown == ["Database class in 8 min (Room 3)"]


def test_a_moved_event_pops_up_again():
    shown = []
    upcoming = [event(minutes=9)]
    checker = Reminders(fetch=lambda: upcoming, notify=shown.append, clock=lambda: NOW)
    checker.check()

    upcoming[0] = event(minutes=5)
    checker.check()

    assert len(shown) == 2


def test_core_offline_is_quiet():
    def offline():
        raise URLError("refused")

    shown = []
    Reminders(fetch=offline, notify=shown.append, clock=lambda: NOW).check()

    assert shown == []


def test_linux_uses_notify_send(monkeypatch):
    calls = []
    monkeypatch.setattr(reminders, "IS_WINDOWS", False)
    monkeypatch.setattr(reminders, "IS_MAC", False)
    monkeypatch.setattr(reminders.shutil, "which", lambda name: "/usr/bin/notify-send")
    monkeypatch.setattr(reminders.subprocess, "run", lambda command, **options: calls.append(command))

    reminders.desktop_notifier(lambda text, title: calls.append("tray"))("Class in 5 min")

    assert calls == [["/usr/bin/notify-send", "Venus reminder", "Class in 5 min"]]


def test_windows_uses_the_tray_toast(monkeypatch):
    calls = []
    monkeypatch.setattr(reminders, "IS_WINDOWS", True)

    reminders.desktop_notifier(lambda text, title: calls.append((text, title)))("Class in 5 min")

    assert calls == [("Class in 5 min", "Venus reminder")]


def test_mac_uses_notification_center(monkeypatch):
    calls = []
    monkeypatch.setattr(reminders, "IS_WINDOWS", False)
    monkeypatch.setattr(reminders, "IS_MAC", True)
    from venus_node.commands import mac_apps

    monkeypatch.setattr(mac_apps, "notify_mac", lambda title, text: calls.append((title, text)))

    reminders.desktop_notifier(lambda text, title: calls.append("tray"))("Class in 5 min")

    assert calls == [("Venus reminder", "Class in 5 min")]
