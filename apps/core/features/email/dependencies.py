from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.engine import Engine

from features.email import mailbox
from features.email.repository import EmailRepository
from storage.database import get_database_engine


def get_email_repository(engine: Annotated[Engine, Depends(get_database_engine)]) -> EmailRepository:
    return EmailRepository(engine)


def get_mail_connectors() -> tuple[Callable, Callable]:
    """How to open IMAP and SMTP connections; tests swap in pretend servers."""
    return mailbox.open_imap, mailbox.open_smtp
