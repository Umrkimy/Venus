from datetime import datetime, timezone
from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from fastapi import status

from config import CoreSettings, get_settings
from features.commands.repository import CommandRecordRepository
from features.home.dependencies import get_home_device_repository
from features.settings.dependencies import get_settings_repository
from features.settings.secrets import encrypt_text
from main import app
from tests.features.nodes.test_nodes_router import (  # noqa: F401  (fixtures)
    TEST_NODE_TOKEN,
    TEST_OWNER_TOKEN,
    client,
    command_records,
    connected_pc_umar,
    override_node_settings,
)

SECRET = Fernet.generate_key().decode()
LOCAL_KEY = "k3y!local-secret"
OWNER = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}


@pytest.fixture(autouse=True)
def home_setup(override_node_settings):  # noqa: F811
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token=TEST_NODE_TOKEN,
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
        secret_key=SECRET,
    )
    devices = app.dependency_overrides[get_home_device_repository]()
    light = devices.add(
        "bedroom light", "light", datetime.now(timezone.utc),
        address="192.168.1.40", tuya_id="bf1234", local_key_encrypted=encrypt_text(LOCAL_KEY, SECRET),
    )
    yield light


def chat(text: str) -> dict:
    response = client.post("/nodes/PC-Umar/chat", json={"message": text}, headers=OWNER)
    assert response.status_code == status.HTTP_200_OK, response.text
    return response.json()


def test_turning_off_a_light_waits_for_approve_and_hides_the_key(
    home_setup, command_records: CommandRecordRepository,  # noqa: F811
):
    with connected_pc_umar():
        body = chat("turn off the bedroom light")

    assert body["type"] == "command"
    assert body["actions"] == [{
        "kind": "command", "command_id": body["command_id"],
        "label": "Bedroom light: off", "title": "Bedroom light: off",
    }]
    # Neither the browser nor the command record ever sees the Tuya key.
    assert LOCAL_KEY not in str(body)
    record = command_records.get(UUID(body["command_id"]))
    assert record.kind == "home"
    assert LOCAL_KEY not in record.payload
    assert record.state == "awaiting_approval"


def test_approve_sends_the_node_the_light_with_its_key(home_setup):
    with connected_pc_umar() as websocket:
        body = chat("set the bedroom light to 40%")
        approved = client.post(f"/commands/{body['command_id']}/approval", json={"approved": True}, headers=OWNER)
        sent = websocket.receive_json()

    assert approved.status_code == status.HTTP_200_OK
    assert LOCAL_KEY not in str(approved.json())
    assert sent["kind"] == "home"
    assert (sent["device"], sent["action"], sent["value"]) == ("light", "brightness", 40)
    assert (sent["address"], sent["tuya_id"], sent["local_key"]) == ("192.168.1.40", "bf1234", LOCAL_KEY)


def test_full_mode_runs_it_at_once(home_setup):
    app.dependency_overrides[get_settings_repository]().set_mode("full")

    with connected_pc_umar() as websocket:
        body = chat("volume up")
        sent = websocket.receive_json()

    assert (sent["device"], sent["action"]) == ("pc", "volume_up")
    assert LOCAL_KEY not in str(body)


def test_a_device_removed_before_approve_is_refused(home_setup):
    with connected_pc_umar():
        body = chat("turn on the bedroom light")
        app.dependency_overrides[get_home_device_repository]().delete(home_setup.id)
        approved = client.post(f"/commands/{body['command_id']}/approval", json={"approved": True}, headers=OWNER)

    assert approved.status_code == status.HTTP_409_CONFLICT
    assert "removed" in approved.json()["detail"]


def test_an_unknown_light_is_an_answer(home_setup):
    with connected_pc_umar():
        body = chat("turn off the kitchen light")

    assert body["type"] == "reply"
    assert "Settings, Home" in body["reply"]


HA_TOKEN = "ha-long-lived-token"


def test_home_assistant_aircon_end_to_end_keeps_the_token_off_the_page(
    home_setup, command_records: CommandRecordRepository,  # noqa: F811
):
    devices = app.dependency_overrides[get_home_device_repository]()
    devices.set_assistant("http://192.168.1.60:8123", encrypt_text(HA_TOKEN, SECRET))
    devices.add("bedroom aircon", "aircon", datetime.now(timezone.utc), ha_entity_id="climate.bedroom_ac")

    with connected_pc_umar() as websocket:
        body = chat("set the aircon to 24")
        approved = client.post(f"/commands/{body['command_id']}/approval", json={"approved": True}, headers=OWNER)
        sent = websocket.receive_json()

    assert body["actions"][0]["label"] == "Bedroom aircon: 24°C"
    assert HA_TOKEN not in str(body) + str(approved.json())
    assert HA_TOKEN not in command_records.get(UUID(body["command_id"])).payload
    assert (sent["device"], sent["action"], sent["value"]) == ("aircon", "temperature", 24)
    assert (sent["ha_url"], sent["ha_token"], sent["ha_entity_id"]) == (
        "http://192.168.1.60:8123", HA_TOKEN, "climate.bedroom_ac",
    )
