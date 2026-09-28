from datetime import datetime, timezone

from sqlalchemy.orm import Session

from features.auth.passwords import hash_password
from features.auth.models.owner_session import OwnerSession
from features.auth.repository import SESSION_LIFETIME, AuthRepository, hash_token
from storage.database import create_database_engine
from storage.base import Base


def test_get_owner_for_session_returns_owner_for_valid_token():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = AuthRepository(engine)
    now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    owner = repository.create_owner("umar", hash_password("pw"), now)
    token = repository.create_session(owner.account_id, now)

    try:
        result = repository.get_owner_for_session(token, now)
        assert result is not None
        assert result.username == "umar"
    finally:
        engine.dispose()


def test_get_owner_for_session_returns_none_after_expiry():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = AuthRepository(engine)
    now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    owner = repository.create_owner("umar", hash_password("pw"), now)
    token = repository.create_session(owner.account_id, now)

    try:
        assert repository.get_owner_for_session(token, now + SESSION_LIFETIME) is None
    finally:
        engine.dispose()


def test_create_session_stores_hash_not_raw_token():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = AuthRepository(engine)
    now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    owner = repository.create_owner("umar", hash_password("pw"), now)
    token = repository.create_session(owner.account_id, now)

    try:
        with Session(engine) as db_session:
            stored = db_session.query(OwnerSession).one()
        assert stored.token_hash == hash_token(token)
        assert stored.token_hash != token
    finally:
        engine.dispose()


def test_has_owner_is_false_until_owner_created():
    engine = create_database_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    repository = AuthRepository(engine)

    try:
        assert not repository.has_owner()
        repository.create_owner("umar", hash_password("pw"), datetime.now(timezone.utc))
        assert repository.has_owner()
    finally:
        engine.dispose()