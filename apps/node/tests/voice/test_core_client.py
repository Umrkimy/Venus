import json

import venus_node.voice.core_client as core_client
from venus_node.config import NodeSettings
from venus_node.voice.core_client import core_http_url, transcribe


def test_core_http_url_from_ws_url():
    assert core_http_url("ws://127.0.0.1:9000/nodes/connect") == "http://127.0.0.1:9000"
    assert core_http_url("wss://venus.test/nodes/connect") == "https://venus.test"


def test_transcribe_posts_wav_with_token_and_returns_text(monkeypatch):
    sent = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"text": "open spotify"}).encode()

    def fake_urlopen(request, timeout):
        sent["request"] = request
        return FakeResponse()

    monkeypatch.setattr(core_client, "urlopen", fake_urlopen)
    settings = NodeSettings(
        device_id="pc", core_dev_token="node-token",
        core_url="ws://core.test:9000/nodes/connect",
    )

    text = transcribe(settings, b"RIFF...")

    request = sent["request"]
    assert text == "open spotify"
    assert request.full_url == "http://core.test:9000/voice/transcribe"
    assert request.data == b"RIFF..."
    assert request.get_header("Authorization") == "Bearer node-token"
    assert request.get_header("Content-type") == "audio/wav"
