import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.auth.models.owner_account import OwnerAccount
from features.auth.models.owner_session import OwnerSession


SESSION_LIFETIME = timedelta(days=7)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthRepository:
    def __init__(self, engine: Engine):
        self._engine = engine

    def create_owner(
        self, username: str, password_hash: str, now: datetime
    ) -> OwnerAccount:
        with Session(self._engine) as session:
            account = OwnerAccount(
                account_id=uuid4(),
                username=username,
                password_hash=password_hash,
                created_at=now,
            )
            session.add(account)
            session.commit()
            session.refresh(account)
            return account

    def get_owner_by_username(self, username: str) -> OwnerAccount | None:
        with Session(self._engine) as session:
            return session.scalar(
                select(OwnerAccount).where(OwnerAccount.username == username)
            )

    def has_owner(self) -> bool:
        with Session(self._engine) as session:
            return session.scalar(select(OwnerAccount.account_id).limit(1)) is not None

    def create_session(self, account_id: UUID, now: datetime) -> str:
        token = secrets.token_urlsafe(32)
        with Session(self._engine) as session:
            owner_session = OwnerSession(
                token_hash=hash_token(token),
                account_id=account_id,
                created_at=now,
                expires_at=now + SESSION_LIFETIME,
            )
            session.add(owner_session)
            session.commit()
        return token

    def get_owner_for_session(
        self, token: str, now: datetime
    ) -> OwnerAccount | None:
        with Session(self._engine) as session:
            owner_session = session.scalar(
                select(OwnerSession).where(
                    OwnerSession.token_hash == hash_token(token)
                )
            )
            if owner_session is None:
                return None

            expires_at = owner_session.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if now >= expires_at:
                return None

            return session.get(OwnerAccount, owner_session.account_id)

    def delete_session(self, token: str) -> None:
        with Session(self._engine) as session:
            owner_session = session.scalar(
                select(OwnerSession).where(
                    OwnerSession.token_hash == hash_token(token)
                )
            )
            if owner_session is not None:
                session.delete(owner_session)
                session.commit()
