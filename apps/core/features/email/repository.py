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
