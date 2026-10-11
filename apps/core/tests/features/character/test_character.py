import json
import struct

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.character.dependencies import get_animation_repository, get_character_repository
from features.character.repository import AnimationRepository, CharacterRepository, is_vrm, is_vrma
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


def upload(name: str, data: bytes = VRM1) -> dict:
    response = client.post(f"/character/models?name={name}", content=data, headers=OWNER_HEADERS)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def test_no_upload_means_the_template(character):
    response = client.get("/character", headers=OWNER_HEADERS)

    assert response.json() == {"custom": False}
    assert client.get("/character/models", headers=OWNER_HEADERS).json() == []
    assert client.get("/character/model", headers=OWNER_HEADERS).status_code == status.HTTP_404_NOT_FOUND


def test_upload_puts_the_model_in_use_and_download_gives_the_same_file(character):
    added = upload("fdl.vrm")

    assert (added["name"], added["size"], added["active"]) == ("fdl.vrm", len(VRM1), True)
    info = client.get("/character", headers=OWNER_HEADERS).json()
    assert info["custom"] is True
    assert info["id"] == added["id"]
    got = client.get("/character/model", headers=OWNER_HEADERS)
    assert got.content == VRM1
    assert got.headers["content-type"] == "model/gltf-binary"


def test_unchanged_model_is_not_sent_again(character):
    upload("a.vrm")
    first = client.get("/character/model", headers=OWNER_HEADERS)

    again = client.get(
        "/character/model",
        headers={**OWNER_HEADERS, "If-None-Match": first.headers["etag"]},
    )

    assert again.status_code == status.HTTP_304_NOT_MODIFIED
    assert again.content == b""


def test_a_new_upload_is_kept_beside_the_old_one(character):
    older = upload("a.vrm")
    newer_file = glb({"VRM": {}}, b"other")

    newer = upload("b.vrm", newer_file)

    listed = client.get("/character/models", headers=OWNER_HEADERS).json()
    assert [(item["id"], item["active"]) for item in listed] == [(older["id"], False), (newer["id"], True)]
    assert client.get("/character/model", headers=OWNER_HEADERS).content == newer_file


def test_switching_to_the_template_keeps_the_model(character):
    added = upload("fdl.vrm")

    response = client.put("/character/active", json={"id": None}, headers=OWNER_HEADERS)

    assert response.json() == {"custom": False}
    assert [item["id"] for item in client.get("/character/models", headers=OWNER_HEADERS).json()] == [added["id"]]
    back = client.put("/character/active", json={"id": added["id"]}, headers=OWNER_HEADERS)
    assert back.json()["name"] == "fdl.vrm"
    assert client.get("/character/model", headers=OWNER_HEADERS).content == VRM1


def test_switching_changes_the_etag(character):
    first = upload("a.vrm")
    upload("b.vrm", glb({"VRM": {}}, b"other"))
    newer_tag = client.get("/character/model", headers=OWNER_HEADERS).headers["etag"]

    client.put("/character/active", json={"id": first["id"]}, headers=OWNER_HEADERS)

    assert client.get("/character/model", headers=OWNER_HEADERS).headers["etag"] != newer_tag


def test_switching_to_a_missing_model_is_404(character):
    response = client.put("/character/active", json={"id": 999}, headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_upload_refuses_a_file_that_is_not_vrm(character):
    response = client.post("/character/models?name=cat.png", content=b"not a model", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert character.list_info() == []


def test_delete_a_model_not_in_use(character):
    older = upload("a.vrm")
    upload("b.vrm")

    response = client.delete(f"/character/models/{older['id']}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert [item["name"] for item in client.get("/character/models", headers=OWNER_HEADERS).json()] == ["b.vrm"]
    missing = client.delete(f"/character/models/{older['id']}", headers=OWNER_HEADERS)
    assert missing.status_code == status.HTTP_404_NOT_FOUND


def test_the_model_in_use_cannot_be_deleted(character):
    added = upload("fdl.vrm")

    response = client.delete(f"/character/models/{added['id']}", headers=OWNER_HEADERS)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert client.get("/character", headers=OWNER_HEADERS).json()["name"] == "fdl.vrm"


def test_character_needs_the_owner_not_a_node(character):
    assert client.get("/character/model").status_code == status.HTTP_401_UNAUTHORIZED
    node = {"Authorization": "Bearer test-node-token"}
    response = client.post("/character/models?name=a.vrm", content=VRM1, headers=node)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


VRMA = glb({"VRMC_vrm_animation": {"specVersion": "1.0"}}, b"keyframes")


@pytest.fixture
def animations(character):
    engine = make_test_engine()
    repository = AnimationRepository(engine)
    app.dependency_overrides[get_animation_repository] = lambda: repository
    yield repository
    engine.dispose()


def test_is_vrma_knows_animations_and_refuses_models():
    assert is_vrma(VRMA)
    assert not is_vrma(VRM1)
    assert not is_vrma(b"not a file at all")


def test_no_animations_means_coded_moves_only(animations):
    response = client.get("/character/animations", headers=OWNER_HEADERS)

    assert response.json() == []


def test_upload_animation_then_list_and_download(animations):
    post = client.post("/character/animations?name=wave.vrma&use=hello", content=VRMA, headers=OWNER_HEADERS)

    assert post.status_code == status.HTTP_201_CREATED
    body = post.json()
    assert (body["name"], body["use"], body["size"]) == ("wave.vrma", "hello", len(VRMA))
    listed = client.get("/character/animations", headers=OWNER_HEADERS).json()
    assert [item["id"] for item in listed] == [body["id"]]
    got = client.get(f"/character/animations/{body['id']}", headers=OWNER_HEADERS)
    assert got.content == VRMA
    assert "immutable" in got.headers["cache-control"]


def test_animation_use_defaults_to_idle(animations):
    post = client.post("/character/animations?name=a.vrma", content=VRMA, headers=OWNER_HEADERS)

    assert post.json()["use"] == "idle"


def test_upload_refuses_a_model_or_unknown_use(animations):
    model = client.post("/character/animations?name=fdl.vrm", content=VRM1, headers=OWNER_HEADERS)
    odd_use = client.post("/character/animations?name=a.vrma&use=dance", content=VRMA, headers=OWNER_HEADERS)

    assert model.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert odd_use.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert animations.list_info() == []


def test_change_animation_use(animations):
    added = client.post("/character/animations?name=a.vrma", content=VRMA, headers=OWNER_HEADERS).json()

    response = client.patch(f"/character/animations/{added['id']}", json={"use": "talking"}, headers=OWNER_HEADERS)

    assert response.json()["use"] == "talking"
    assert animations.list_info()[0].use == "talking"


def test_delete_animation_and_missing_ones_are_404(animations):
    added = client.post("/character/animations?name=a.vrma", content=VRMA, headers=OWNER_HEADERS).json()

    first = client.delete(f"/character/animations/{added['id']}", headers=OWNER_HEADERS)
    again = client.delete(f"/character/animations/{added['id']}", headers=OWNER_HEADERS)

    assert first.status_code == status.HTTP_204_NO_CONTENT
    assert again.status_code == status.HTTP_404_NOT_FOUND
    assert client.get(f"/character/animations/{added['id']}", headers=OWNER_HEADERS).status_code == 404
    patch = client.patch(f"/character/animations/{added['id']}", json={"use": "idle"}, headers=OWNER_HEADERS)
    assert patch.status_code == status.HTTP_404_NOT_FOUND


def test_animations_need_the_owner(animations):
    assert client.get("/character/animations").status_code == status.HTTP_401_UNAUTHORIZED
    node = {"Authorization": "Bearer test-node-token"}
    response = client.post("/character/animations?name=a.vrma", content=VRMA, headers=node)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
