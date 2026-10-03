import json
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from venus_node.config import NodeSettings

HTTP_SCHEMES = {"ws": "http", "wss": "https"}


def core_http_url(ws_url: str) -> str:
    # The Node only knows Core's WebSocket address; HTTP routes share its host.
    parts = urlsplit(ws_url)
    return f"{HTTP_SCHEMES.get(parts.scheme, parts.scheme)}://{parts.netloc}"


def transcribe(settings: NodeSettings, wav: bytes) -> str:
    request = Request(
        f"{core_http_url(settings.core_url)}/voice/transcribe",
        data=wav,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.core_dev_token}",
            "Content-Type": "audio/wav",
        },
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)["text"]
