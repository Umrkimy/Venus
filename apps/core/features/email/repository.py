from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from features.email.models.email_account import EmailAccount


class DuplicateAccountError(Exception):
    pass


class EmailRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_all(self) -> list[EmailAccount]:
        with Session(self.engine) as session:
            return list(session.scalars(select(EmailAccount).order_by(EmailAccount.created_at)))

    def get(self, account_id: UUID) -> EmailAccount | None:
        with Session(self.engine) as session:
            return session.get(EmailAccount, account_id)

    def add(self, now: datetime, **fields) -> EmailAccount:
        account = EmailAccount(created_at=now, **fields)
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(account)
            try:
                session.commit()
            except IntegrityError as exc:
                raise DuplicateAccountError(account.address) from exc
        return account

    def delete(self, account_id: UUID) -> bool:
        with Session(self.engine) as session:
            account = session.get(EmailAccount, account_id)
            if account is None:
                return False
            session.delete(account)
            session.commit()
            return True

    def add_signed_in(self, kind: str, address: str, display_name: str, now: datetime) -> EmailAccount:
        """A mailbox reached through the Google or Microsoft sign-in (no password here)."""
        with Session(self.engine, expire_on_commit=False) as session:
            found = session.scalars(select(EmailAccount).where(EmailAccount.address == address)).first()
            if found is not None:
                if found.kind != kind:
                    raise DuplicateAccountError(address)
                found.display_name = display_name
                session.commit()
                return found
            account = EmailAccount(address=address, display_name=display_name, kind=kind, created_at=now)
            session.add(account)
            session.commit()
            return account

    def delete_signed_in(self, kind: str) -> None:
        with Session(self.engine) as session:
            for account in session.scalars(select(EmailAccount).where(EmailAccount.kind == kind)):
                session.delete(account)
            session.commit()
