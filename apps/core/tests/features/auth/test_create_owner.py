import pytest

from features.auth.create_owner import create_owner_account
from features.auth.passwords import verify_password
from features.auth.repository import AuthRepository
from tests.database import make_test_engine


VALID_PASSWORD = "correct horse battery"


@pytest.fixture
def repository():
    engine = make_test_engine()
    yield AuthRepository(engine)
    engine.dispose()


def test_create_owner_account_saves_owner(repository):
    create_owner_account(repository, "umar", VALID_PASSWORD)

    owner = repository.get_owner_by_username("umar")
    assert owner is not None
    assert verify_password(VALID_PASSWORD, owner.password_hash)


def test_create_owner_account_rejects_second_owner(repository):
    create_owner_account(repository, "umar", VALID_PASSWORD)

    with pytest.raises(ValueError, match="already exists"):
        create_owner_account(repository, "someone", VALID_PASSWORD)


def test_create_owner_account_rejects_short_password(repository):
    with pytest.raises(ValueError, match="at least 12 characters"):
        create_owner_account(repository, "umar", "short")

    assert not repository.has_owner()
