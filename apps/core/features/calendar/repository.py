from datetime import datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from features.calendar.models.calendar_account import CalendarAccount


class CalendarRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_all(self) -> list[CalendarAccount]:
        with Session(self.engine) as session:
            return list(session.scalars(select(CalendarAccount).order_by(CalendarAccount.provider)))

    def get(self, provider: str) -> CalendarAccount | None:
        with Session(self.engine) as session:
            return session.get(CalendarAccount, provider)

    def save_client(self, provider: str, client_id: str, client_secret_encrypted: str | None) -> CalendarAccount:
        """A new or changed OAuth app. A changed app signs you out: its old tokens don't fit it."""
        with Session(self.engine, expire_on_commit=False) as session:
            account = session.get(CalendarAccount, provider)
            if account is None:
                if client_secret_encrypted is None:
                    raise ValueError("A new calendar app needs its client secret")
                account = CalendarAccount(provider, client_id, client_secret_encrypted)
                session.add(account)
            else:
                if account.client_id != client_id:
                    account.refresh_token_encrypted = None
                    account.account_email = None
                    account.connected_at = None
                account.client_id = client_id
                if client_secret_encrypted is not None:
                    account.client_secret_encrypted = client_secret_encrypted
            session.commit()
            return account

    def connect(self, provider: str, refresh_token_encrypted: str, email: str | None, now: datetime) -> None:
        with Session(self.engine) as session:
            account = session.get(CalendarAccount, provider)
            account.refresh_token_encrypted = refresh_token_encrypted
            account.account_email = email
            account.connected_at = now
            session.commit()

    def save_refresh_token(self, provider: str, refresh_token_encrypted: str) -> None:
        # Microsoft hands out a new refresh token with each refresh.
        with Session(self.engine) as session:
            account = session.get(CalendarAccount, provider)
            if account is not None:
                account.refresh_token_encrypted = refresh_token_encrypted
                session.commit()

    def disconnect(self, provider: str) -> bool:
        with Session(self.engine) as session:
            account = session.get(CalendarAccount, provider)
            if account is None:
                return False
            session.delete(account)
            session.commit()
            return True
