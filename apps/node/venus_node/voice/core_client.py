import json
from collections.abc import Iterator
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from venus_node.config import NodeSettings

HTTP_SCHEMES = {"ws": "http", "wss": "https"}


def core_http_url(ws_url: str) -> str:
    # The Node only knows Core's WebSocket address; HTTP routes share its host.
    parts = urlsplit(ws_url)
    return f"{HTTP_SCHEMES.get(parts.scheme, parts.scheme)}://{parts.netloc}"


def _open(settings: NodeSettings, path: str, data: bytes, content_type: str):
    request = Request(
        f"{core_http_url(settings.core_url)}{path}",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.core_dev_token}",
            "Content-Type": content_type,
        },
    )
    # Luna can take a few seconds (her answer plus a line after a command).
    return urlopen(request, timeout=60)


def _post(settings: NodeSettings, path: str, data: bytes, content_type: str) -> bytes:
    with _open(settings, path, data, content_type) as response:
        return response.read()


def transcribe(settings: NodeSettings, wav: bytes) -> str:
    return json.loads(_post(settings, "/voice/transcribe", wav, "audio/wav"))["text"]


def chat(settings: NodeSettings, message: str, conversation_id: str | None) -> dict:
    """The same chat the web uses: Luna answers, commands get proposed."""
    body = {"message": message, "conversation_id": conversation_id}
    path = f"/nodes/{quote(settings.device_id)}/chat"
    return json.loads(_post(settings, path, json.dumps(body).encode(), "application/json"))


def speak_stream(settings: NodeSettings, text: str) -> tuple[int, Iterator[bytes]]:
    """Luna's voice as raw 16-bit mono PCM pieces, and their sample rate.

    The pieces come while Fish is still making the rest, so playing can start at once.
    """
    body = json.dumps({"text": text}).encode()
    response = _open(settings, "/voice/speak/stream", body, "application/json")
    rate = int(response.headers.get("X-Sample-Rate", 44100))

    def pieces() -> Iterator[bytes]:
        with response:
            # About 50 ms of audio per piece.
            while piece := response.read(4096):
                yield piece

    return rate, pieces()
