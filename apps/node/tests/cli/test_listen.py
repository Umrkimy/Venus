import io
from urllib.error import HTTPError

import venus_node.cli.listen as listen
from venus_node.config import NodeSettings
from venus_node.voice.conversation import VoiceChat

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
