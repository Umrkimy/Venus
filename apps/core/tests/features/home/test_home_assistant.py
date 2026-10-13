"""Home Assistant in Settings, Home, against a pretend Home Assistant."""

from datetime import datetime, timedelta, timezone

import httpx2
import pytest
from cryptography.fernet import Fernet
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.home.commands import home_command, without_secrets
from features.home.dependencies import get_home_assistant_transport, get_home_device_repository
from features.home.repository import HomeDeviceRepository
from features.home.rules import HomeIntent, HomeTextError
from features.settings.secrets import decrypt_text
from main import app
from tests.database import make_test_engine

SECRET = Fernet.generate_key().decode()
OWNER = {"Authorization": "Bearer test-owner-token"}
HA = {"url": "http://192.168.1.60:8123", "token": "long-lived-token"}
STATES = [
    {"entity_id": "light.bedroom", "attributes": {"friendly_name": "Bedroom Light"}},
    {"entity_id": "climate.bedroom_ac", "attributes": {"friendly_name": "Bedroom A/C (Daikin)"}},
    {"entity_id": "media_player.living_room", "attributes": {}},
    {"entity_id": "scene.movie_time", "attributes": {"friendly_name": "Movie time"}},
    {"entity_id": "switch.kettle", "attributes": {"friendly_name": "Kettle"}},
    {"entity_id": "lock.front_door", "attributes": {"friendly_name": "Front door"}},  # never offered
    {"entity_id": "sensor.temperature", "attributes": {"friendly_name": "Temp"}},
]

client = TestClient(app)
seen: list[httpx2.Request] = []


def fake_home_assistant(request: httpx2.Request) -> httpx2.Response:
    seen.append(request)
    if request.headers.get("Authorization") != "Bearer long-lived-token":
        return httpx2.Response(401)
    return httpx2.Response(200, json=STATES)


@pytest.fixture(autouse=True)
def devices():
    engine = make_test_engine()
    repository = HomeDeviceRepository(engine)
    seen.clear()
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token="test-owner-token",
        database_url="sqlite+pysqlite:///:memory:",
        secret_key=SECRET,
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_home_device_repository] = lambda: repository
    app.dependency_overrides[get_home_assistant_transport] = lambda: httpx2.MockTransport(fake_home_assistant)
    yield repository
    app.dependency_overrides.clear()
    engine.dispose()


def test_connect_keeps_the_token_encrypted_and_hidden(devices: HomeDeviceRepository):
    assert client.get("/home/assistant", headers=OWNER).json() == {"url": None, "connected": False}

    response = client.put("/home/assistant", json=HA, headers=OWNER)

    assert response.status_code == status.HTTP_200_OK
    assert "long-lived" not in response.text
    assert client.get("/home/assistant", headers=OWNER).json() == {"url": HA["url"], "connected": True}
    assert decrypt_text(devices.get_assistant().token_encrypted, SECRET) == "long-lived-token"


def test_changing_the_address_keeps_the_token(devices: HomeDeviceRepository):
    client.put("/home/assistant", json=HA, headers=OWNER)

    client.put("/home/assistant", json={"url": "http://homeassistant.local:8123"}, headers=OWNER)

    row = devices.get_assistant()
    assert row.url == "http://homeassistant.local:8123"
    assert decrypt_text(row.token_encrypted, SECRET) == "long-lived-token"


@pytest.mark.parametrize(
    "body",
    [
        {"url": "http://192.168.1.60:8123"},  # first time needs the token
        {"url": "https://myhome.ui.nabu.casa", "token": "t"},  # not the home network
        {"url": "http://192.168.1.60:8123", "token": "has spaces"},
    ],
)
def test_bad_connections_are_refused(body):
    assert client.put("/home/assistant", json=body, headers=OWNER).status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_entities_lists_only_what_venus_can_control_with_spoken_names():
    client.put("/home/assistant", json=HA, headers=OWNER)
    client.post(
        "/home/devices",
        json={"name": "movie time", "kind": "scene", "ha_entity_id": "scene.movie_time"},
        headers=OWNER,
    )

    response = client.get("/home/assistant/entities", headers=OWNER)

    assert response.status_code == status.HTTP_200_OK
    assert str(seen[-1].url) == "http://192.168.1.60:8123/api/states"
    by_id = {entity["entity_id"]: entity for entity in response.json()}
    assert set(by_id) == {
        "light.bedroom", "climate.bedroom_ac", "media_player.living_room", "scene.movie_time", "switch.kettle",
    }
    assert by_id["climate.bedroom_ac"] == {
        "entity_id": "climate.bedroom_ac",
        "kind": "aircon",
        "friendly_name": "Bedroom A/C (Daikin)",
        "name": "bedroom a c daikin",
        "added_as": None,
    }
    assert by_id["media_player.living_room"]["name"] == "living room"
    assert by_id["switch.kettle"]["kind"] == "plug"
    assert by_id["scene.movie_time"]["added_as"] == "movie time"


def test_entities_says_why_it_failed():
    assert client.get("/home/assistant/entities", headers=OWNER).status_code == status.HTTP_409_CONFLICT

    client.put("/home/assistant", json=HA | {"token": "wrong"}, headers=OWNER)
    response = client.get("/home/assistant/entities", headers=OWNER)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "didn't accept the token" in response.json()["detail"]


def test_unreachable_home_assistant_suggests_the_ip():
    def down(request):
        raise httpx2.ConnectError("no route", request=request)

    app.dependency_overrides[get_home_assistant_transport] = lambda: httpx2.MockTransport(down)
    client.put("/home/assistant", json=HA | {"url": "http://homeassistant.local:8123"}, headers=OWNER)

    response = client.get("/home/assistant/entities", headers=OWNER)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "try its IP address" in response.json()["detail"]


def test_imported_device_needs_a_matching_kind_and_a_connection():
    aircon = {"name": "bedroom aircon", "kind": "aircon", "ha_entity_id": "climate.bedroom_ac"}

    assert client.post("/home/devices", json=aircon, headers=OWNER).status_code == status.HTTP_409_CONFLICT
    client.put("/home/assistant", json=HA, headers=OWNER)
    wrong = client.post("/home/devices", json=aircon | {"kind": "light"}, headers=OWNER)
    right = client.post("/home/devices", json=aircon, headers=OWNER)

    assert wrong.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert right.status_code == status.HTTP_201_CREATED
    assert right.json()["ha_entity_id"] == "climate.bedroom_ac"
    # Air-con only comes from Home Assistant.
    no_ha = client.post("/home/devices", json={"name": "ac", "kind": "aircon"}, headers=OWNER)
    assert no_ha.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_disconnect_forgets_the_token_and_imported_devices(devices: HomeDeviceRepository):
    client.put("/home/assistant", json=HA, headers=OWNER)
    client.post("/home/devices", json={"name": "kettle", "kind": "plug", "ha_entity_id": "switch.kettle"}, headers=OWNER)
    client.post("/home/devices", json={"name": "laptop", "kind": "pc", "mac": "AA:BB:CC:DD:EE:FF"}, headers=OWNER)

    assert client.delete("/home/assistant", headers=OWNER).status_code == status.HTTP_204_NO_CONTENT

    assert devices.get_assistant() is None
    assert [device.name for device in devices.list_all()] == ["laptop"]


def test_command_carries_the_token_but_records_never_do(devices: HomeDeviceRepository):
    client.put("/home/assistant", json=HA, headers=OWNER)
    device = devices.add("bedroom aircon", "aircon", datetime.now(timezone.utc), ha_entity_id="climate.bedroom_ac")
    intent = HomeIntent("aircon", "mode", "Bedroom aircon: cool", device.id, mode="cool")

    command = home_command(intent, device, "pc-home", SECRET, assistant=devices.get_assistant())

    assert (command.ha_url, command.ha_token, command.ha_entity_id, command.mode) == (
        HA["url"], "long-lived-token", "climate.bedroom_ac", "cool",
    )
    assert command.expires_at > datetime.now(timezone.utc) + timedelta(minutes=4)
    assert "ha_token" not in without_secrets(command.model_dump(mode="json"))
    with pytest.raises(HomeTextError, match="isn't connected"):
        home_command(intent, device, "pc-home", SECRET, assistant=None)


def test_assistant_needs_the_owner():
    assert client.get("/home/assistant").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/home/assistant/entities").status_code == status.HTTP_401_UNAUTHORIZED
