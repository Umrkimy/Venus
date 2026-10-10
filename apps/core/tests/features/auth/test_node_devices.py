from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from features.auth.models.node_device import NodeDevice
from features.auth.repository import (
    MAIN_DEVICE_NAME,
    AuthRepository,
    MainDeviceError,
    hash_token,
)
from tests.database import make_test_engine

ENV_TOKEN = "env-node-token"
NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def repository():
    engine = make_test_engine()
    yield AuthRepository(engine)
    engine.dispose()


def test_env_token_becomes_the_main_pc_on_first_use(repository):
    device = repository.find_node_device(ENV_TOKEN, ENV_TOKEN, NOW)

    assert device is not None
    assert device.name == MAIN_DEVICE_NAME
    assert device.is_main is True
    # Using it again finds the same row instead of adding another.
    assert repository.find_node_device(ENV_TOKEN, ENV_TOKEN, NOW).id == device.id
    assert len(repository.list_node_devices()) == 1


def test_main_pc_cannot_be_revoked(repository):
    device = repository.find_node_device(ENV_TOKEN, ENV_TOKEN, NOW)

    with pytest.raises(MainDeviceError):
        repository.revoke_node_device(device.id, NOW)
    assert repository.find_node_device(ENV_TOKEN, ENV_TOKEN, NOW) is not None


def test_new_env_token_replaces_the_main_pc(repository):
    old = repository.find_node_device(ENV_TOKEN, ENV_TOKEN, NOW)
    repository.claim_node_device(old, "pc-umar", NOW)

    new = repository.find_node_device("rotated-token", "rotated-token", NOW)

    # The old token stops working and the same PC can claim its name again.
    assert repository.find_node_device(ENV_TOKEN, "rotated-token", NOW) is None
    assert repository.claim_node_device(new, "pc-umar", NOW) is True
    assert [d.is_main for d in repository.list_node_devices()] == [False, True]


def test_unknown_token_is_rejected(repository):
    assert repository.find_node_device("guess", ENV_TOKEN, NOW) is None
    assert repository.list_node_devices() == []


def test_new_device_token_is_stored_only_as_a_hash(repository):
    device, token = repository.create_node_device("  Laptop  ", NOW)

    with Session(repository._engine) as session:
        saved = session.scalar(select(NodeDevice))
    assert saved.name == "Laptop"
    assert saved.token_hash == hash_token(token)
    assert token not in saved.token_hash
    assert repository.find_node_device(token, ENV_TOKEN, NOW).id == device.id


def test_token_locks_to_the_first_device_id(repository):
    device, _ = repository.create_node_device("Laptop", NOW)

    assert repository.claim_node_device(device, "laptop-1", NOW) is True
    assert repository.claim_node_device(device, "laptop-1", NOW) is True
    assert repository.claim_node_device(device, "pc-umar", NOW) is False
    assert repository.list_node_devices()[0].last_seen_at is not None


def test_two_tokens_cannot_claim_the_same_device_id(repository):
    first, _ = repository.create_node_device("PC", NOW)
    second, _ = repository.create_node_device("Copy", NOW)
    repository.claim_node_device(first, "pc-umar", NOW)

    assert repository.claim_node_device(second, "pc-umar", NOW) is False


def test_revoked_device_cannot_claim(repository):
    device, token = repository.create_node_device("Laptop", NOW)
    repository.revoke_node_device(device.id, NOW)

    assert repository.find_node_device(token, ENV_TOKEN, NOW) is None
    assert repository.claim_node_device(device, "laptop-1", NOW) is False
