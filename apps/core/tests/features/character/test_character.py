import json
import struct

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.character.dependencies import get_character_repository
from features.character.repository import CharacterRepository, is_vrm
from main import app
from tests.database import make_test_engine

TEST_OWNER_TOKEN = "test-owner-token"
OWNER_HEADERS = {"Authorization": f"Bearer {TEST_OWNER_TOKEN}"}

client = TestClient(app)


def glb(extensions: dict, body: bytes = b"") -> bytes:
    # The smallest glTF binary: header, JSON chunk, then whatever else.
    text = json.dumps({"asset": {"version": "2.0"}, "extensions": extensions}).encode()
    text += b" " * (-len(text) % 4)
    total = 12 + 8 + len(text) + len(body)
    return struct.pack("<4sII", b"glTF", 2, total) + struct.pack("<I4s", len(text), b"JSON") + text + body


VRM1 = glb({"VRMC_vrm": {"specVersion": "1.0"}}, b"mesh bytes")


@pytest.fixture
def character():
    engine = make_test_engine()
    repository = CharacterRepository(engine)
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token=TEST_OWNER_TOKEN,
        database_url="postgresql+psycopg://venus:test-password@127.0.0.1:5432/venus",
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_character_repository] = lambda: repository
    yield repository
    app.dependency_overrides.clear()
    engine.dispose()


def test_is_vrm_knows_vrm_1_and_0():
    assert is_vrm(VRM1)
    assert is_vrm(glb({"VRM": {}}))


def test_is_vrm_refuses_plain_gltf_and_other_files():
    assert not is_vrm(glb({}))
    assert not is_vrm(b"\x89PNG\r\n\x1a\n" + b"\0" * 40)
    assert not is_vrm(b"glTF")


def test_no_upload_means_the_template(character):
    response = client.get("/character", headers=OWNER_HEADERS)

    assert response.json() == {"custom": False}
    assert client.get("/character/model", headers=OWNER_HEADERS).status_code == status.HTTP_404_NOT_FOUND


def test_upload_then_download_gives_the_same_file(character):
    put = client.put("/character/model?name=fdl.vrm", content=VRM1, headers=OWNER_HEADERS)

    assert put.status_code == status.HTTP_200_OK
    assert put.json()["custom"] is True
    assert put.json()["name"] == "fdl.vrm"
    assert put.json()["size"] == len(VRM1)
    got = client.get("/character/model", headers=OWNER_HEADERS)
    assert got.content == VRM1
    assert got.headers["content-type"] == "model/gltf-binary"


def test_unchanged_model_is_not_sent_again(character):
    client.put("/character/model?name=a.vrm", content=VRM1, headers=OWNER_HEADERS)
    first = client.get("/character/model", headers=OWNER_HEADERS)

    again = client.get(
        "/character/model",
        headers={**OWNER_HEADERS, "If-None-Match": first.headers["etag"]},
    )

    assert again.status_code == status.HTTP_304_NOT_MODIFIED
    assert again.content == b""


def test_a_new_upload_replaces_the_old_one(character):
    client.put("/character/model?name=a.vrm", content=VRM1, headers=OWNER_HEADERS)
    newer = glb({"VRM": {}}, b"other")

    client.put("/character/model?name=b.vrm", content=newer, headers=OWNER_HEADERS)

    assert client.get("/character", headers=OWNER_HEADERS).json()["name"] == "b.vrm"
    assert client.get("/character/model", headers=OWNER_HEADERS).content == newer


def test_upload_refuses_a_file_that_is_not_vrm(character):
    response = client.put("/character/model?name=cat.png", content=b"not a model", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert character.get_info() is None


def test_delete_goes_back_to_the_template(character):
    client.put("/character/model?name=a.vrm", content=VRM1, headers=OWNER_HEADERS)

    response = client.delete("/character/model", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert client.get("/character", headers=OWNER_HEADERS).json() == {"custom": False}


def test_character_needs_the_owner_not_a_node(character):
    assert client.get("/character/model").status_code == status.HTTP_401_UNAUTHORIZED
    node = {"Authorization": "Bearer test-node-token"}
    response = client.put("/character/model?name=a.vrm", content=VRM1, headers=node)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
