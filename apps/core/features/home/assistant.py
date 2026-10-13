"""Talking to the owner's Home Assistant from Core: only to list what's there.

Commands themselves go through the Node, which sits on the home network.
Core may run in Docker, where names like homeassistant.local often don't
resolve, so the errors suggest the IP address.
"""

import re

import httpx2

from venus_protocol.schemas.commands import HOME_ASSISTANT_DOMAINS

KIND_BY_DOMAIN = {domain: kind for kind, domains in HOME_ASSISTANT_DOMAINS.items() for domain in domains}


class AssistantError(Exception):
    """Home Assistant couldn't be reached or said no; the message is for the page."""


def spoken_name(name: str) -> str:
    """A friendly name as something you'd say: lowercase, letters, digits, spaces."""
    name = re.sub(r"[^a-z0-9 '-]+", " ", name.lower())
    name = re.sub(r"\s+", " ", name).strip(" '-")
    return name[:40].strip()


async def list_entities(url: str, token: str, transport: httpx2.AsyncBaseTransport | None = None) -> list[dict]:
    try:
        async with httpx2.AsyncClient(transport=transport, timeout=10) as client:
            response = await client.get(f"{url}/api/states", headers={"Authorization": f"Bearer {token}"})
    except httpx2.HTTPError as exc:
        raise AssistantError(
            f"Couldn't reach Home Assistant at {url}. If you used a name like "
            "homeassistant.local, try its IP address (for example http://192.168.1.50:8123)."
        ) from exc
    if response.status_code == 401:
        raise AssistantError("Home Assistant didn't accept the token. Make a new long-lived token and save it again.")
    if response.status_code != 200:
        raise AssistantError(f"Home Assistant answered {response.status_code}.")
    entities = []
    for state in response.json():
        entity_id = str(state.get("entity_id", ""))
        kind = KIND_BY_DOMAIN.get(entity_id.split(".")[0])
        if kind is None or not re.fullmatch(r"[a-z_]+\.[a-z0-9_]+", entity_id):
            continue
        friendly = str((state.get("attributes") or {}).get("friendly_name") or entity_id.split(".")[1].replace("_", " "))
        entities.append({
            "entity_id": entity_id,
            "kind": kind,
            "friendly_name": friendly[:100],
            "name": spoken_name(friendly) or spoken_name(entity_id.split(".")[1].replace("_", " ")),
        })
    return sorted(entities, key=lambda entity: (entity["kind"], entity["name"]))
