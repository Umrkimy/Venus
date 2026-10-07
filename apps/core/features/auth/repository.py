import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.auth.models.node_device import NodeDevice
from features.auth.models.owner_account import OwnerAccount
from features.auth.models.owner_session import OwnerSession


# A login ends after a week without use, and after 30 days no matter what.
SESSION_IDLE_LIMIT = timedelta(days=7)
SESSION_MAX_AGE = timedelta(days=30)
# "Last active" is saved at most this often, not on every request.
LAST_SEEN_STEP = timedelta(minutes=5)
USER_AGENT_LIMIT = 300

# Name for the token from VENUS_CORE_DEV_NODE_TOKEN, saved on first use.
MAIN_DEVICE_NAME = "Main PC"


class MainDeviceError(Exception):
    """The main PC can't be revoked from the web; change its .env token instead."""


class ActiveDeviceError(Exception):
    """Only revoked devices can be deleted, so a working token never vanishes by accident."""


def _aware(moment: datetime | None) -> datetime | None:
    # SQLite gives times back without a time zone; Postgres keeps it.
    if moment is not None and moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def _session_alive(owner_session: OwnerSession, now: datetime) -> bool:
    if now >= _aware(owner_session.expires_at):
        return False
    last_used = _aware(owner_session.last_seen_at) or _aware(owner_session.created_at)
    # last_seen_at is saved in LAST_SEEN_STEP steps, so allow that much slack.
    return now - last_used < SESSION_IDLE_LIMIT + LAST_SEEN_STEP


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

    def create_session(
        self, account_id: UUID, now: datetime, user_agent: str | None = None
    ) -> str:
        token = secrets.token_urlsafe(32)
        with Session(self._engine) as session:
            owner_session = OwnerSession(
                token_hash=hash_token(token),
                id=uuid4(),
                account_id=account_id,
                created_at=now,
                expires_at=now + SESSION_MAX_AGE,
                user_agent=user_agent[:USER_AGENT_LIMIT] if user_agent else None,
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

            if not _session_alive(owner_session, now):
                return None

            last_seen = _aware(owner_session.last_seen_at)
            if last_seen is None or now - last_seen >= LAST_SEEN_STEP:
                owner_session.last_seen_at = now
                session.commit()

            return session.get(OwnerAccount, owner_session.account_id)

    def list_sessions(self, now: datetime) -> list[OwnerSession]:
        """Signed-in browsers, newest first; expired ones are left out."""
        with Session(self._engine) as session:
            sessions = session.scalars(
                select(OwnerSession).order_by(OwnerSession.created_at.desc())
            ).all()
        return [s for s in sessions if _session_alive(s, now)]

    def session_id_for_token(self, token: str) -> UUID | None:
        with Session(self._engine) as session:
            return session.scalar(
                select(OwnerSession.id).where(OwnerSession.token_hash == hash_token(token))
            )

    def delete_session_by_id(self, session_id: UUID) -> bool:
        with Session(self._engine) as session:
            result = session.execute(
                delete(OwnerSession).where(OwnerSession.id == session_id)
            )
            session.commit()
        return result.rowcount > 0

    def delete_other_sessions(self, keep_token: str | None) -> int:
        """Sign out every browser except the one with keep_token."""
        query = delete(OwnerSession)
        if keep_token is not None:
            query = query.where(OwnerSession.token_hash != hash_token(keep_token))
        with Session(self._engine) as session:
            result = session.execute(query)
            session.commit()
        return result.rowcount

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

    def delete_expired_sessions(self, account_id: UUID, now: datetime) -> None:
        with Session(self._engine) as session:
            owner_sessions = session.scalars(
                select(OwnerSession).where(OwnerSession.account_id == account_id)
            ).all()
            for owner_session in owner_sessions:
                if not _session_alive(owner_session, now):
                    session.delete(owner_session)
            session.commit()

    def create_node_device(self, name: str, now: datetime) -> tuple[NodeDevice, str]:
        """Return the new device and its token. The token is never stored."""
        token = secrets.token_urlsafe(32)
        device = self._add_node_device(name.strip(), hash_token(token), now)
        return device, token

    def _add_node_device(self, name: str, token_hash: str, now: datetime) -> NodeDevice:
        with Session(self._engine, expire_on_commit=False) as session:
            device = NodeDevice(id=uuid4(), name=name, token_hash=token_hash, created_at=now)
            session.add(device)
            session.commit()
        return device

    def _add_main_device(self, token_hash: str, now: datetime) -> NodeDevice:
        with Session(self._engine, expire_on_commit=False) as session:
            # A new .env token replaces the old main one: retire it and free
            # its device_id so the same PC can claim it with the new token.
            for old in session.scalars(select(NodeDevice).where(NodeDevice.is_main)):
                old.is_main = False
                old.device_id = None
                old.revoked_at = now
            session.flush()
            device = NodeDevice(
                id=uuid4(),
                name=MAIN_DEVICE_NAME,
                token_hash=token_hash,
                created_at=now,
                is_main=True,
            )
            session.add(device)
            session.commit()
        return device

    def find_node_device(
        self, token: str, env_token: str, now: datetime
    ) -> NodeDevice | None:
        """Return the active device for this token, or None.

        The .env token becomes the main device the first time it is used.
        """
        token_hash = hash_token(token)
        with Session(self._engine, expire_on_commit=False) as session:
            device = session.scalar(
                select(NodeDevice).where(NodeDevice.token_hash == token_hash)
            )
        if device is None and hmac.compare_digest(token, env_token):
            device = self._add_main_device(token_hash, now)
        if device is None or device.revoked_at is not None:
            return None
        return device

    def claim_node_device(
        self, device: NodeDevice, device_id: str, now: datetime
    ) -> bool:
        """Lock a new token to the first device_id; later only that one fits."""
        with Session(self._engine) as session:
            saved = session.get(NodeDevice, device.id)
            if saved is None or saved.revoked_at is not None:
                return False
            if saved.device_id is None:
                taken = session.scalar(
                    select(NodeDevice.id).where(NodeDevice.device_id == device_id)
                )
                if taken is not None:
                    return False
                saved.device_id = device_id
            elif saved.device_id != device_id:
                return False
            saved.last_seen_at = now
            session.commit()
        return True

    def list_node_devices(self) -> list[NodeDevice]:
        with Session(self._engine) as session:
            return list(
                session.scalars(select(NodeDevice).order_by(NodeDevice.created_at)).all()
            )

    def delete_node_device(self, device_id: UUID) -> bool:
        """Remove a revoked device row. Active ones must be revoked first."""
        with Session(self._engine) as session:
            device = session.get(NodeDevice, device_id)
            if device is None:
                return False
            if device.revoked_at is None:
                raise ActiveDeviceError
            session.delete(device)
            session.commit()
        return True

    def revoke_node_device(self, device_id: UUID, now: datetime) -> NodeDevice | None:
        with Session(self._engine, expire_on_commit=False) as session:
            device = session.get(NodeDevice, device_id)
            if device is None:
                return None
            if device.is_main:
                raise MainDeviceError
            if device.revoked_at is None:
                device.revoked_at = now
                session.commit()
        return device
