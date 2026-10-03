import json

import pytest

import venus_node.voice.core_client as core_client
from venus_node.config import NodeSettings
from venus_node.voice.core_client import chat, core_http_url, speak, transcribe

SETTINGS = NodeSettings(
    device_id="pc-umar", core_dev_token="node-token",
    core_url="ws://core.test:9000/nodes/connect",
)


@pytest.fixture
def core(monkeypatch):
    """Fake Core: records each request and answers with `core["body"]`."""
    sent = {"body": b"{}"}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return sent["body"]

    def fake_urlopen(request, timeout):
        sent["request"] = request
        return FakeResponse()

    monkeypatch.setattr(core_client, "urlopen", fake_urlopen)
    return sent


def test_core_http_url_from_ws_url():
    assert core_http_url("ws://127.0.0.1:9000/nodes/connect") == "http://127.0.0.1:9000"
    assert core_http_url("wss://venus.test/nodes/connect") == "https://venus.test"


def test_transcribe_posts_wav_with_token_and_returns_text(core):
    core["body"] = json.dumps({"text": "open spotify"}).encode()

    text = transcribe(SETTINGS, b"RIFF...")

    request = core["request"]
    assert text == "open spotify"
    assert request.full_url == "http://core.test:9000/voice/transcribe"
    assert request.data == b"RIFF..."
    assert request.get_header("Authorization") == "Bearer node-token"
    assert request.get_header("Content-type") == "audio/wav"


def test_chat_posts_message_and_conversation_to_this_pc(core):
    core["body"] = json.dumps({"type": "reply", "reply": "hi love", "conversation_id": "c1"}).encode()

    answer = chat(SETTINGS, "hello", "c1")

    request = core["request"]
    assert answer["reply"] == "hi love"
    assert request.full_url == "http://core.test:9000/nodes/pc-umar/chat"
    assert json.loads(request.data) == {"message": "hello", "conversation_id": "c1"}
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("Authorization") == "Bearer node-token"


def test_speak_posts_text_and_returns_audio(core):
    core["body"] = b"ID3 mp3 bytes"

    audio = speak(SETTINGS, "opening spotify")

    request = core["request"]
    assert audio == b"ID3 mp3 bytes"
    assert request.full_url == "http://core.test:9000/voice/speak"
    assert json.loads(request.data) == {"text": "opening spotify"}
