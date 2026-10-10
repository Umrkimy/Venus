import json

import pytest

import venus_node.voice.core_client as core_client
from venus_node.config import NodeSettings
from venus_node.voice.core_client import chat, core_http_url, report_state, speak_stream, transcribe

SETTINGS = NodeSettings(
    device_id="pc-umar", core_dev_token="node-token",
    core_url="ws://core.test:9000/nodes/connect",
)


@pytest.fixture
def core(monkeypatch):
    """Fake Core: records each request and answers with `core["body"]`."""
    sent = {"body": b"{}", "headers": {}}

    class FakeResponse:
        def __init__(self):
            self.left = sent["body"]
            self.headers = sent["headers"]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            sent["closed"] = True
            return False

        def read(self, size=-1):
            size = len(self.left) if size < 0 else size
            piece, self.left = self.left[:size], self.left[size:]
            return piece

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
    assert json.loads(request.data) == {"message": "hello", "conversation_id": "c1", "voice": True}
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("Authorization") == "Bearer node-token"


def test_speak_stream_reads_pieces_and_sample_rate(core):
    core["body"] = b"x" * 5000
    core["headers"] = {"X-Sample-Rate": "22050"}

    rate, pieces = speak_stream(SETTINGS, "opening spotify")
    received = list(pieces)

    request = core["request"]
    assert rate == 22050
    assert [len(piece) for piece in received] == [4096, 904]
    assert core["closed"]
    assert request.full_url == "http://core.test:9000/voice/speak/stream"
    assert json.loads(request.data) == {"text": "opening spotify"}


def test_report_state_puts_state_and_reads_web_watching(core):
    core["body"] = json.dumps(
        {"web_watching": True, "web_listening": True, "stop": False, "end_pause_ms": 2000},
    ).encode()

    reply = report_state(SETTINGS, "speaking", "hi " * 600, muted=False)

    request = core["request"]
    assert reply == (True, True, False, 2000)
    assert request.full_url == "http://core.test:9000/voice/state"
    assert request.get_method() == "PUT"
    body = json.loads(request.data)
    assert body["state"] == "speaking"
    assert body["muted"] is False
    # Cut to what Core accepts, or Core would answer 422 and the orb would never hide.
    assert len(body["subtitle"]) == 1000


def test_report_state_keeps_the_default_pause_with_an_older_core(core):
    core["body"] = json.dumps({"web_watching": False, "web_listening": False, "stop": False}).encode()

    assert report_state(SETTINGS, "idle", "", muted=False)[3] == 1500
