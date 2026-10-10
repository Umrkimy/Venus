from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from features.auth.passwords import hash_password
from features.auth.models.owner_session import OwnerSession
from features.auth.repository import (
    LAST_SEEN_STEP,
    SESSION_IDLE_LIMIT,
    SESSION_MAX_AGE,
    AuthRepository,
    hash_token,
)
from tests.database import make_test_engine


def test_get_owner_for_session_returns_owner_for_valid_token():
    engine = make_test_engine()
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


def test_get_owner_for_session_returns_none_after_max_age():
    engine = make_test_engine()
    repository = AuthRepository(engine)
    now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    owner = repository.create_owner("umar", hash_password("pw"), now)
    token = repository.create_session(owner.account_id, now)

    try:
        # Used every few days, so never idle, but still ends at the hard limit.
        moment = now
        while moment + timedelta(days=3) < now + SESSION_MAX_AGE:
            moment += timedelta(days=3)
            assert repository.get_owner_for_session(token, moment) is not None
        assert repository.get_owner_for_session(token, now + SESSION_MAX_AGE) is None
    finally:
        engine.dispose()


def test_create_session_stores_hash_not_raw_token():
    engine = make_test_engine()
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


def test_delete_expired_sessions_keeps_live_sessions():
    engine = make_test_engine()
    repository = AuthRepository(engine)
    now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    owner = repository.create_owner("umar", hash_password("pw"), now)
    repository.create_session(owner.account_id, now - SESSION_MAX_AGE)
    repository.create_session(
        owner.account_id, now - SESSION_IDLE_LIMIT - LAST_SEEN_STEP
    )
    live_token = repository.create_session(owner.account_id, now)

    try:
        repository.delete_expired_sessions(owner.account_id, now)

        with Session(engine) as db_session:
            stored = db_session.query(OwnerSession.token_hash).all()
        assert [row.token_hash for row in stored] == [hash_token(live_token)]
    finally:
        engine.dispose()


def test_has_owner_is_false_until_owner_created():
    engine = make_test_engine()
    repository = AuthRepository(engine)

    try:
        assert not repository.has_owner()
        repository.create_owner("umar", hash_password("pw"), datetime.now(timezone.utc))
        assert repository.has_owner()
    finally:
        engine.dispose()


def test_get_owner_for_session_returns_none_after_week_unused():
    engine = make_test_engine()
    repository = AuthRepository(engine)
    now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    owner = repository.create_owner("umar", hash_password("pw"), now)
    token = repository.create_session(owner.account_id, now)

    try:
        later = now + SESSION_IDLE_LIMIT + LAST_SEEN_STEP
        assert repository.get_owner_for_session(token, later) is None
    finally:
        engine.dispose()


def test_using_a_session_pushes_idle_limit_forward():
    engine = make_test_engine()
    repository = AuthRepository(engine)
    now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    owner = repository.create_owner("umar", hash_password("pw"), now)
    token = repository.create_session(owner.account_id, now)

    try:
        used = now + timedelta(days=6)
        assert repository.get_owner_for_session(token, used) is not None
        # Ten days after login, but only four since last use.
        assert repository.get_owner_for_session(token, now + timedelta(days=10)) is not None
    finally:
        engine.dispose()


def test_list_sessions_leaves_out_idle_sessions():
    engine = make_test_engine()
    repository = AuthRepository(engine)
    now = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    owner = repository.create_owner("umar", hash_password("pw"), now)
    repository.create_session(owner.account_id, now - timedelta(days=8))
    repository.create_session(owner.account_id, now)

    try:
        assert len(repository.list_sessions(now)) == 1
    finally:
        engine.dispose()
