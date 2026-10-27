from datetime import datetime, timedelta, timezone
from threading import Event
from urllib.error import URLError

from venus_node.app import reminders
from venus_node.app.reminders import Reminders, reminder_text, spoken_text, voice_sayer
from venus_node.voice.status import IDLE, SPEAKING, THINKING, Status

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


def test_spoken_text_is_a_sentence():
    assert spoken_text(event(), NOW) == "Heads up, Database class starts in 8 minutes, in Room 3."
    assert spoken_text(event(minutes=1, location=""), NOW) == "Heads up, Database class starts in 1 minute."
    assert spoken_text(event(minutes=0, location=""), NOW) == "Heads up, Database class is starting now."


def test_venus_says_each_reminder_once_with_the_popup():
    shown, said = [], []
    checker = Reminders(fetch=lambda: [event()], notify=shown.append, clock=lambda: NOW, say=said.append)

    checker.check()
    checker.check()

    assert shown == ["Database class in 8 min (Room 3)"]
    assert said == ["Heads up, Database class starts in 8 minutes, in Room 3."]


def fake_voice(monkeypatch):
    played = []
    from venus_node.voice import core_client, player

    monkeypatch.setattr(core_client, "speak_stream", lambda settings, text: (24000, iter([b"\0\0"])))

    def play(pieces, rate, on_start=None, **options):
        if on_start:
            on_start()
        played.append(list(pieces))

    monkeypatch.setattr(player, "play_pcm", play)
    return played


def test_sayer_speaks_when_idle_and_goes_back_to_idle(monkeypatch):
    played = fake_voice(monkeypatch)
    status, seen = Status(), []
    original = status.set
    monkeypatch.setattr(status, "set", lambda state, subtitle="": (seen.append(state), original(state, subtitle)))

    voice_sayer(object(), status, Event())("Heads up, Gym starts in 10 minutes.")

    assert len(played) == 1
    assert seen == [SPEAKING, IDLE]
    assert status.report()[0] == IDLE


def test_sayer_stays_quiet_when_muted_or_busy(monkeypatch):
    played = fake_voice(monkeypatch)
    muted = Event()
    muted.set()
    voice_sayer(object(), Status(), muted)("Heads up.")

    busy = Status()
    busy.set(THINKING)
    voice_sayer(object(), busy, Event())("Heads up.")

    assert played == []
    assert busy.report()[0] == THINKING
