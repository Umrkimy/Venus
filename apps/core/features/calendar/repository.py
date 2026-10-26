from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from features.calendar.models.calendar_account import CalendarAccount
from features.calendar.models.ics_calendar import IcsCalendar
from features.calendar.models.venus_event import VenusEvent


class DuplicateNameError(Exception):
    pass


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

    def connect(
        self, provider: str, refresh_token_encrypted: str, email: str | None, now: datetime, mail: bool = False,
    ) -> None:
        with Session(self.engine) as session:
            account = session.get(CalendarAccount, provider)
            account.refresh_token_encrypted = refresh_token_encrypted
            account.account_email = email
            account.connected_at = now
            account.mail = mail
            account.signed_out_at = None
            session.commit()

    def mark_signed_out(self, provider: str, now: datetime) -> None:
        with Session(self.engine) as session:
            account = session.get(CalendarAccount, provider)
            if account is not None and account.signed_out_at is None:
                account.signed_out_at = now
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

    def list_ics(self) -> list[IcsCalendar]:
        with Session(self.engine) as session:
            return list(session.scalars(select(IcsCalendar).order_by(IcsCalendar.name)))

    def add_ics(
        self, name: str, now: datetime, url_encrypted: str | None = None, content: str | None = None,
    ) -> IcsCalendar:
        calendar = IcsCalendar(name.strip(), now, url_encrypted=url_encrypted, content=content)
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(calendar)
            try:
                session.commit()
            except IntegrityError as exc:
                raise DuplicateNameError(calendar.name) from exc
        return calendar

    def delete_ics(self, calendar_id: UUID) -> bool:
        with Session(self.engine) as session:
            calendar = session.get(IcsCalendar, calendar_id)
            if calendar is None:
                return False
            session.delete(calendar)
            session.commit()
            return True

    def venus_events(self, start: datetime, end: datetime) -> list[VenusEvent]:
        """Venus's own events that overlap start..end."""
        with Session(self.engine) as session:
            query = select(VenusEvent).where(VenusEvent.start < end, VenusEvent.end >= start).order_by(VenusEvent.start)
            return list(session.scalars(query))

    def add_venus_event(self, event: VenusEvent) -> VenusEvent:
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(event)
            session.commit()
        return event

    def update_venus_event(self, event_id: UUID, **fields) -> bool:
        with Session(self.engine) as session:
            event = session.get(VenusEvent, event_id)
            if event is None:
                return False
            for name, value in fields.items():
                setattr(event, name, value)
            session.commit()
            return True

    def delete_venus_event(self, event_id: UUID) -> bool:
        with Session(self.engine) as session:
            event = session.get(VenusEvent, event_id)
            if event is None:
                return False
            session.delete(event)
            session.commit()
            return True
