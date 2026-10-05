import io
from threading import Event
from urllib.error import HTTPError

import numpy as np

import venus_node.cli.listen as listen
from venus_node.config import NodeSettings
from venus_node.voice.conversation import VoiceChat
from venus_node.voice.status import SPEAKING, Status

SETTINGS = NodeSettings(device_id="pc", core_dev_token="t", core_url="ws://core.test/nodes/connect")


class FakeStream:
    def __init__(self, events):
        self.events = events

    def stop(self):
        self.events.append("mic off")

    def start(self):
        self.events.append("mic on")


def setup(monkeypatch, text="open spotify", reply="Opening Spotify, love."):
    events = []
    monkeypatch.setattr(listen, "transcribe", lambda settings, wav: text)
    monkeypatch.setattr(listen, "speak", lambda settings, said: events.append(f"speak {said}") or b"mp3")
    monkeypatch.setattr(listen, "play_mp3", lambda mp3: events.append("play"))
    voice = VoiceChat(lambda message, conversation_id: {"reply": reply, "conversation_id": "c1"})
    return events, voice


def test_answer_says_luna_reply_with_the_mic_off(monkeypatch, capsys):
    events, voice = setup(monkeypatch)

    listen.answer(SETTINGS, voice, b"pcm", FakeStream(events))

    assert events == ["speak Opening Spotify, love.", "mic off", "play", "mic on"]
    assert "Luna: Opening Spotify, love." in capsys.readouterr().out


def test_answer_skips_chat_when_nothing_was_heard(monkeypatch):
    events, _ = setup(monkeypatch, text="")
    asked = []
    voice = VoiceChat(lambda message, conversation_id: asked.append(message))

    listen.answer(SETTINGS, voice, b"pcm", FakeStream(events))

    assert asked == []
    assert events == []


def test_answer_explains_when_venus_is_not_running(monkeypatch, capsys):
    events, _ = setup(monkeypatch)

    def not_connected(message, conversation_id):
        raise HTTPError("http://core.test/nodes/pc/chat", 409, "Conflict", {}, io.BytesIO())

    listen.answer(SETTINGS, VoiceChat(not_connected), b"pcm", FakeStream(events))

    assert "Run start-venus.cmd first" in capsys.readouterr().out
    assert events == []


def test_answer_says_when_core_heard_only_silence(monkeypatch, capsys):
    events, voice = setup(monkeypatch)
    body = io.BytesIO(b'{"detail": "Check your mic is plugged in and not muted."}')

    def silence(settings, wav):
        raise HTTPError("http://core.test/voice/transcribe", 422, "Unprocessable", {}, body)

    monkeypatch.setattr(listen, "transcribe", silence)

    listen.answer(SETTINGS, voice, b"pcm", FakeStream(events))

    assert "Check your mic is plugged in" in capsys.readouterr().out
    assert events == []


def test_answer_turns_the_mic_back_on_if_playback_fails(monkeypatch):
    events, voice = setup(monkeypatch)

    def broken_speakers(mp3):
        raise RuntimeError("no output device")

    monkeypatch.setattr(listen, "play_mp3", broken_speakers)

    try:
        listen.answer(SETTINGS, voice, b"pcm", FakeStream(events))
    except RuntimeError:
        pass

    assert events[-1] == "mic on"


def test_answer_tells_the_circle_thinking_then_speaking(monkeypatch):
    events, voice = setup(monkeypatch)
    status = Status()
    seen = []
    monkeypatch.setattr(listen, "play_mp3", lambda mp3: seen.append(status.snapshot()[0]))

    listen.answer(SETTINGS, voice, b"pcm", FakeStream(events), status)

    assert seen == [SPEAKING]


def test_answer_cancel_asks_luna_nothing(monkeypatch, capsys):
    events, _ = setup(monkeypatch, text="Never mind.")
    asked = []

    outcome = listen.answer(SETTINGS, VoiceChat(lambda m, c: asked.append(m)), b"pcm", FakeStream(events))

    assert outcome is None
    assert asked == [] and events == []
    assert "Cancelled." in capsys.readouterr().out


def test_answer_stop_listening_returns_sleep_without_luna(monkeypatch):
    events, _ = setup(monkeypatch, text="Hey Venus, stop listening.")
    asked = []

    outcome = listen.answer(SETTINGS, VoiceChat(lambda m, c: asked.append(m)), b"pcm", FakeStream(events))

    assert outcome == "sleep"
    assert asked == [] and events == []


class FakeListener:
    def __init__(self, on_frame=None):
        self.on_frame = on_frame or (lambda: None)

    def heard(self, frame):
        self.on_frame()
        return False

    def reset(self):
        pass


class FakeMic:
    """A mic that logs opens and closes and plays silent frames."""

    def __init__(self, events, on_close=None):
        self.events = events
        self.on_close = on_close or (lambda: None)

    def __enter__(self):
        self.events.append("open")
        return self

    def __exit__(self, *exc):
        self.events.append("close")
        self.on_close()

    def read(self, frames):
        return np.zeros((frames, 1), dtype=np.int16), False


def test_listen_loop_closes_the_mic_when_muted():
    events = []
    status = Status()
    muted = Event()
    # Muting mid-stream must close the mic; closing ends the test loop.
    mic = FakeMic(events, on_close=status.close)

    listen.listen_loop(SETTINGS, FakeListener(muted.set), FakeListener(), status, muted, lambda: mic)

    assert events == ["open", "close"]
    assert status.snapshot()[0] == "idle"


def test_listen_loop_reopens_the_mic_after_unmute(monkeypatch):
    events = []
    status = Status()
    muted = Event()
    opens = []

    def open_stream():
        opens.append(1)
        if len(opens) == 2:
            status.close()  # Second open proves unmute worked; stop there.
        return FakeMic(events)

    def mute_once():
        if len(opens) == 1:
            muted.set()

    # While muted the loop naps; "unmute" during the nap.
    monkeypatch.setattr(listen.time, "sleep", lambda seconds: muted.clear())

    listen.listen_loop(SETTINGS, FakeListener(mute_once), FakeListener(), status, muted, open_stream)

    assert events == ["open", "close", "open", "close"]


DEVICES = [
    {"name": "Speakers (Realtek(R) Audio)", "max_input_channels": 0},
    {"name": "Microphone (Micstream Virtual A", "max_input_channels": 1},
    {"name": "Microphone (Realtek(R) Audio)", "max_input_channels": 2},
]


def test_find_mic_picks_the_named_input():
    assert listen.find_mic("realtek", DEVICES) == 2  # Not the speakers with the same name.


def test_find_mic_empty_means_windows_default():
    assert listen.find_mic("", DEVICES) is None


def test_find_mic_unknown_name_falls_back_to_default(capsys):
    assert listen.find_mic("blue yeti", DEVICES) is None
    assert "using the Windows default mic" in capsys.readouterr().out

