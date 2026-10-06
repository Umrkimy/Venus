import io
from threading import Event
from urllib.error import HTTPError

import numpy as np

import venus_node.cli.listen as listen
from venus_node.config import NodeSettings
from venus_node.voice.conversation import VoiceChat
from venus_node.voice.status import SPEAKING, THINKING, Status
from venus_node.voice.timing import Timer

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
    monkeypatch.setattr(
        listen, "speak_stream", lambda settings, said: events.append(f"speak {said}") or (44100, iter([b"pc"])),
    )

    def play(pieces, rate, on_start, stop=None):
        on_start()
        events.append("play")

    monkeypatch.setattr(listen, "play_pcm", play)
    voice = VoiceChat(lambda message, conversation_id: {"reply": reply, "conversation_id": "c1"})
    return events, voice


def test_answer_says_luna_reply_with_the_mic_off(monkeypatch, capsys):
    events, voice = setup(monkeypatch)

    listen.answer(SETTINGS, voice, b"pc", FakeStream(events))

    assert events == ["mic off", "speak Opening Spotify, love.", "play", "mic on"]
    assert "Luna: Opening Spotify, love." in capsys.readouterr().out


def test_answer_skips_chat_when_nothing_was_heard(monkeypatch):
    events, _ = setup(monkeypatch, text="")
    asked = []
    voice = VoiceChat(lambda message, conversation_id: asked.append(message))

    listen.answer(SETTINGS, voice, b"pc", FakeStream(events))

    assert asked == []
    assert events == []


def test_answer_explains_when_venus_is_not_running(monkeypatch, capsys):
    events, _ = setup(monkeypatch)

    def not_connected(message, conversation_id):
        raise HTTPError("http://core.test/nodes/pc/chat", 409, "Conflict", {}, io.BytesIO())

    listen.answer(SETTINGS, VoiceChat(not_connected), b"pc", FakeStream(events))

    assert "Run start-venus.cmd first" in capsys.readouterr().out
    assert events == []


def test_answer_says_when_core_heard_only_silence(monkeypatch, capsys):
    events, voice = setup(monkeypatch)
    body = io.BytesIO(b'{"detail": "Check your mic is plugged in and not muted."}')

    def silence(settings, wav):
        raise HTTPError("http://core.test/voice/transcribe", 422, "Unprocessable", {}, body)

    monkeypatch.setattr(listen, "transcribe", silence)

    listen.answer(SETTINGS, voice, b"pc", FakeStream(events))

    assert "Check your mic is plugged in" in capsys.readouterr().out
    assert events == []


def test_answer_turns_the_mic_back_on_if_playback_fails(monkeypatch):
    events, voice = setup(monkeypatch)

    def broken_speakers(pieces, rate, on_start, stop=None):
        raise RuntimeError("no output device")

    monkeypatch.setattr(listen, "play_pcm", broken_speakers)

    try:
        listen.answer(SETTINGS, voice, b"pc", FakeStream(events))
    except RuntimeError:
        pass

    assert events[-1] == "mic on"


def test_answer_tells_the_circle_thinking_then_speaking(monkeypatch):
    events, voice = setup(monkeypatch)
    status = Status()
    seen = []
    def play(pieces, rate, on_start, stop=None):
        seen.append(status.snapshot()[0])  # Still thinking: no sound yet.
        on_start()
        seen.append(status.snapshot()[0])

    monkeypatch.setattr(listen, "play_pcm", play)

    listen.answer(SETTINGS, voice, b"pc", FakeStream(events), status)

    assert seen == [THINKING, SPEAKING]


def test_answer_cancel_asks_luna_nothing(monkeypatch, capsys):
    events, _ = setup(monkeypatch, text="Never mind.")
    asked = []

    outcome = listen.answer(SETTINGS, VoiceChat(lambda m, c: asked.append(m)), b"pc", FakeStream(events))

    # Cancel also ends a conversation.
    assert outcome == listen.CANCEL
    assert asked == [] and events == []
    assert "Cancelled." in capsys.readouterr().out


def test_answer_stop_listening_returns_sleep_without_luna(monkeypatch):
    events, _ = setup(monkeypatch, text="Hey Venus, stop listening.")
    asked = []

    outcome = listen.answer(SETTINGS, VoiceChat(lambda m, c: asked.append(m)), b"pc", FakeStream(events))

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


def test_answer_logs_time_per_step(monkeypatch):
    events, voice = setup(monkeypatch)
    timer = Timer(clock=lambda: 0.0)

    listen.answer(SETTINGS, voice, b"pc", FakeStream(events), timer=timer)

    assert timer.report() == "Timing: transcribe 0.0 s, chat 0.0 s, voice 0.0 s, playback 0.0 s"


def test_answer_mute_asks_luna_nothing(monkeypatch):
    events, _ = setup(monkeypatch, text="Hey Venus, mute the mic for me.")
    asked = []

    outcome = listen.answer(SETTINGS, VoiceChat(lambda m, c: asked.append(m)), b"pc", FakeStream(events))

    assert outcome == "mute"
    assert asked == [] and events == []


class HearsOnce(FakeListener):
    def __init__(self):
        super().__init__()
        self.done = False

    def heard(self, frame):
        heard, self.done = not self.done, True
        return heard


def test_hear_calls_the_tray_mute_when_you_say_mute(monkeypatch):
    monkeypatch.setattr(listen, "answer", lambda *args: "mute")
    muted = Event()
    status = Status()

    listen.hear(SETTINGS, None, HearsOnce(), FakeListener(), status, FakeMic([]), muted, muted.set)

    assert muted.is_set()
    assert status.snapshot()[0] == "idle"


def test_answer_says_so_when_the_voice_stream_breaks(monkeypatch, capsys):
    from http.client import IncompleteRead

    events, voice = setup(monkeypatch)

    def cut_off(pieces, rate, on_start, stop=None):
        raise IncompleteRead(b"")

    monkeypatch.setattr(listen, "play_pcm", cut_off)

    listen.answer(SETTINGS, voice, b"pc", FakeStream(events))

    assert "Luna's voice isn't available" in capsys.readouterr().out
    assert events[-1] == "mic on"



def test_answer_drops_luna_reply_when_stopped_while_she_thinks(monkeypatch, capsys):
    events, voice = setup(monkeypatch)
    status = Status()

    def ask_then_stop(message, conversation_id):
        status.request_stop()  # Web stop button while Core works on her answer.
        return {"reply": "Opening Spotify, love.", "conversation_id": "c1"}

    listen.answer(SETTINGS, VoiceChat(ask_then_stop), b"pc", FakeStream(events), status)

    assert not any(event.startswith("speak") for event in events)
    assert "Stopped before Luna spoke." in capsys.readouterr().out


def test_answer_passes_the_stop_to_the_player(monkeypatch):
    events, voice = setup(monkeypatch)
    status = Status()
    given = []
    monkeypatch.setattr(listen, "play_pcm", lambda pieces, rate, on_start, stop=None: given.append(stop))

    listen.answer(SETTINGS, voice, b"pc", FakeStream(events), status)

    assert given == [status.stop]


def test_an_old_stop_does_not_cut_the_next_turn(monkeypatch):
    events, voice = setup(monkeypatch)
    status = Status()
    status.request_stop()  # Pressed while nothing was playing.

    listen.answer(SETTINGS, voice, b"pc", FakeStream(events), status)

    assert "play" in events


class HearsStop(FakeListener):
    """Hears "stop venus" once Luna is talking."""

    def __init__(self, status):
        super().__init__()
        self.status = status

    def heard(self, frame):
        return self.status.snapshot()[0] == SPEAKING

    def reset(self):
        pass


def test_saying_stop_venus_keeps_the_mic_on_and_stops_her(monkeypatch):
    events, voice = setup(monkeypatch)
    status = Status()

    def play(pieces, rate, on_start, stop=None):
        on_start()
        assert stop.wait(2)  # The mic thread heard "stop venus".
        events.append("cut off")

    monkeypatch.setattr(listen, "play_pcm", play)
    mic = FakeMic(events)

    listen.answer(SETTINGS, voice, b"pc", mic, status, stop_listener=HearsStop(status))

    # The mic stayed on to hear you (no "mic off"), and her line was cut.
    assert "mic off" not in events
    assert "cut off" in events


def test_hear_ignores_hey_venus_while_the_web_listens(monkeypatch):
    answered = []
    monkeypatch.setattr(listen, "answer", lambda *args: answered.append(True))
    status = Status()
    status.set_web_listening(True)

    class Closes(HearsOnce):
        def heard(self, frame):
            status.close()  # Would only be reached if the frame were checked.
            return super().heard(frame)

    frames = [0]

    class ThreeFrames(FakeMic):
        def read(self, size):
            frames[0] += 1
            if frames[0] > 3:
                status.close()
            return super().read(size)

    listen.hear(SETTINGS, None, Closes(), FakeListener(), status, ThreeFrames([]), Event())

    assert answered == []



def test_hear_ignores_hey_venus_while_a_muted_web_tab_is_in_front(monkeypatch):
    # On the web only the web listens: its mute must not hand you back to the PC mic.
    answered = []
    monkeypatch.setattr(listen, "answer", lambda *args: answered.append(True))
    status = Status()
    status.set_web_watching(True)

    frames = [0]

    class ThreeFrames(FakeMic):
        def read(self, size):
            frames[0] += 1
            if frames[0] > 3:
                status.close()
            return super().read(size)

    listen.hear(SETTINGS, None, HearsOnce(), FakeListener(), status, ThreeFrames([]), Event())

    assert answered == []


def test_goodbye_gets_a_bye_from_luna_then_ends_the_conversation(monkeypatch):
    events, voice = setup(monkeypatch, text="Okay, goodbye.", reply="Bye babe.")

    outcome = listen.answer(SETTINGS, voice, b"pc", FakeStream(events))

    assert "speak Bye babe." in events
    assert outcome == listen.GOODBYE


def test_nothing_heard_ends_the_conversation(monkeypatch):
    events, voice = setup(monkeypatch, text="")

    assert listen.answer(SETTINGS, voice, b"pc", FakeStream(events)) == listen.NOTHING


class LoudMic(FakeMic):
    def read(self, frames):
        return np.full((frames, 1), 3000, dtype=np.int16), False


def test_conversation_keeps_listening_without_hey_venus_until_goodbye(monkeypatch):
    outcomes = iter([None, None, listen.GOODBYE])
    calls = []

    def fake_answer(*args):
        calls.append(True)
        return next(outcomes)

    monkeypatch.setattr(listen, "answer", fake_answer)
    status = Status()

    class WakeOnceThenClose(HearsOnce):
        def heard(self, frame):
            if self.done:
                status.close()  # Back to waiting for "Hey Venus": the test is over.
            return super().heard(frame)

    listen.hear(SETTINGS, None, WakeOnceThenClose(), FakeListener(), status, LoudMic([]), Event())

    # One "Hey Venus", three sentences answered.
    assert len(calls) == 3


def test_quiet_after_an_answer_ends_the_conversation_for_free(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(listen, "answer", lambda *args: calls.append(True))
    status = Status()

    class WakeOnceThenClose(HearsOnce):
        def heard(self, frame):
            if self.done:
                status.close()
            return super().heard(frame)

    listen.hear(SETTINGS, None, WakeOnceThenClose(), FakeListener(), status, FakeMic([]), Event())

    # The silent follow-up never went to Core.
    assert len(calls) == 1
    assert "conversation ended" in capsys.readouterr().out
