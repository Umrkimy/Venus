import json
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from venus_node.config import NodeSettings

HTTP_SCHEMES = {"ws": "http", "wss": "https"}


def core_http_url(ws_url: str) -> str:
    # The Node only knows Core's WebSocket address; HTTP routes share its host.
    parts = urlsplit(ws_url)
    return f"{HTTP_SCHEMES.get(parts.scheme, parts.scheme)}://{parts.netloc}"


def _post(settings: NodeSettings, path: str, data: bytes, content_type: str) -> bytes:
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
    with urlopen(request, timeout=60) as response:
        return response.read()


def transcribe(settings: NodeSettings, wav: bytes) -> str:
    return json.loads(_post(settings, "/voice/transcribe", wav, "audio/wav"))["text"]


def chat(settings: NodeSettings, message: str, conversation_id: str | None) -> dict:
    """The same chat the web uses: Luna answers, commands get proposed."""
    body = {"message": message, "conversation_id": conversation_id}
    path = f"/nodes/{quote(settings.device_id)}/chat"
    return json.loads(_post(settings, path, json.dumps(body).encode(), "application/json"))


def speak(settings: NodeSettings, text: str) -> bytes:
    """Luna's voice for the text, as mp3."""
    body = json.dumps({"text": text}).encode()
    return _post(settings, "/voice/speak", body, "application/json")
