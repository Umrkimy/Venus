from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from cryptography.fernet import InvalidToken
from fastapi import Depends, HTTPException, status
from sqlalchemy.engine import Engine

from config import CoreSettings, get_settings
from features.calendar.dependencies import get_calendar_service
from features.calendar.providers import CalendarError
from features.calendar.service import CalendarService
from features.email import mailbox
from features.email.backends import GmailBackend, GraphBackend, ImapBackend
from features.email.mailbox import MailError, MailSettings
from features.email.models.email_account import EmailAccount
from features.email.repository import EmailRepository
from features.settings.secrets import decrypt_text
from storage.database import get_database_engine


def get_email_repository(engine: Annotated[Engine, Depends(get_database_engine)]) -> EmailRepository:
    return EmailRepository(engine)


def get_mail_connectors() -> tuple[Callable, Callable]:
    """How to open IMAP and SMTP connections; tests swap in pretend servers."""
    return mailbox.open_imap, mailbox.open_smtp


def settings_for(account: EmailAccount, secret_key: str) -> MailSettings:
    try:
        password = decrypt_text(account.password_encrypted, secret_key)
    except InvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The saved app password can't be read. Remove the account and add it again.",
        ) from exc
    return MailSettings(
        address=account.address,
        display_name=account.display_name,
        imap_host=account.imap_host,
        imap_port=account.imap_port,
        imap_security=account.imap_security,
        smtp_host=account.smtp_host,
        smtp_port=account.smtp_port,
        smtp_security=account.smtp_security,
        username=account.username,
        password=password,
    )


MailBackend = ImapBackend | GmailBackend | GraphBackend


def backend_for(account: EmailAccount, secret_key: str, connectors: tuple, calendar: CalendarService) -> MailBackend:
    if account.kind == "imap":
        return ImapBackend(settings_for(account, secret_key), connectors[0], connectors[1])
    # Signed in with Google or Microsoft: only the address and name matter for sending.
    sender = MailSettings(account.address, account.display_name, "", 0, "ssl", "", 0, "ssl", "", "")

    async def token() -> str:
        try:
            return await calendar.access_token(account.kind)
        except CalendarError as exc:
            raise MailError(str(exc)) from exc

    kind = GmailBackend if account.kind == "google" else GraphBackend
    return kind(sender, token, calendar.transport)


def get_email_account(
    account_id: UUID, repository: Annotated[EmailRepository, Depends(get_email_repository)],
) -> EmailAccount:
    account = repository.get(account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such email account")
    return account


def get_mail_backend(
    account: Annotated[EmailAccount, Depends(get_email_account)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    connectors: Annotated[tuple, Depends(get_mail_connectors)],
    calendar: Annotated[CalendarService, Depends(get_calendar_service)],
) -> MailBackend:
    """The mailbox of the account in the path: IMAP, Gmail or Outlook."""
    return backend_for(account, settings.secret_key, connectors, calendar)
