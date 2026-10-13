import pytest
from cryptography.fernet import Fernet
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.home.dependencies import get_home_device_repository
from features.home.repository import HomeDeviceRepository
from features.settings.secrets import decrypt_text
from main import app
from tests.database import make_test_engine

SECRET = Fernet.generate_key().decode()
OWNER = {"Authorization": "Bearer test-owner-token"}
LIGHT = {
    "name": "Bedroom Light",
    "kind": "light",
    "address": "192.168.1.40",
    "tuya_id": "bf1234",
    "local_key": "k3y!local-secret",
}

client = TestClient(app)


@pytest.fixture(autouse=True)
def devices():
    engine = make_test_engine()
    repository = HomeDeviceRepository(engine)
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token="test-owner-token",
        database_url="sqlite+pysqlite:///:memory:",
        secret_key=SECRET,
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_home_device_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()
    engine.dispose()


def test_add_a_light_keeps_its_key_encrypted_and_hidden(devices: HomeDeviceRepository):
    response = client.post("/home/devices", json=LIGHT, headers=OWNER)

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["name"] == "bedroom light"  # lowercase, how you say it
    assert body["has_key"] is True
    assert "k3y" not in response.text
    saved = devices.list_all()[0]
    assert decrypt_text(saved.local_key_encrypted, SECRET) == "k3y!local-secret"
    assert client.get("/home/devices", headers=OWNER).json() == [body]


def test_tv_and_pc_need_less(devices: HomeDeviceRepository):
    tv = client.post("/home/devices", json={"name": "tv", "kind": "tv", "address": "192.168.1.50"}, headers=OWNER)
    pc = client.post("/home/devices", json={"name": "laptop", "kind": "pc", "mac": "AA:BB:CC:DD:EE:FF"}, headers=OWNER)

    assert tv.status_code == pc.status_code == status.HTTP_201_CREATED


@pytest.mark.parametrize(
    "change",
    [
        {"address": "8.8.8.8"},  # internet address
        {"local_key": None},  # light without a key
        {"kind": "pc"},  # pc without a MAC
        {"name": "x; drop table"},  # odd characters in a name
    ],
)
def test_bad_devices_are_refused(change):
    response = client.post("/home/devices", json=LIGHT | change, headers=OWNER)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_same_name_twice_is_409():
    client.post("/home/devices", json=LIGHT, headers=OWNER)

    response = client.post("/home/devices", json=LIGHT | {"name": "bedroom light"}, headers=OWNER)

    assert response.status_code == status.HTTP_409_CONFLICT


def test_delete_then_404():
    device_id = client.post("/home/devices", json=LIGHT, headers=OWNER).json()["id"]

    assert client.delete(f"/home/devices/{device_id}", headers=OWNER).status_code == status.HTTP_204_NO_CONTENT
    assert client.delete(f"/home/devices/{device_id}", headers=OWNER).status_code == status.HTTP_404_NOT_FOUND


def test_home_needs_the_owner():
    assert client.get("/home/devices").status_code == status.HTTP_401_UNAUTHORIZED
