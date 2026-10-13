import asyncio
import re
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from config import CoreSettings, get_settings
from features.auth.dependencies import require_owner
from features.chat.dependencies import get_chat_provider
from features.chat.provider import ChatProvider
from features.calendar.dependencies import get_calendar_service
from features.calendar.providers import CalendarError
from features.calendar.service import CalendarService
from features.email import assistant, mailbox
from features.email.backends import GmailBackend, GraphBackend, ImapBackend
from features.email.dependencies import get_email_repository, get_mail_connectors
from features.email.mailbox import MailError, MailMessage, MailSettings, MailSummary, Outgoing
from features.email.models.email_account import EmailAccount
from features.email.repository import DuplicateAccountError, EmailRepository
from features.settings.router import encrypt_key
from features.settings.secrets import decrypt_text

router = APIRouter(prefix="/email", dependencies=[Depends(require_owner)])

# Where common providers keep their servers, so most people only type an address.
PRESETS = {
    "gmail.com": ("imap.gmail.com", 993, "smtp.gmail.com", 465, "ssl"),
    "googlemail.com": ("imap.gmail.com", 993, "smtp.gmail.com", 465, "ssl"),
    "icloud.com": ("imap.mail.me.com", 993, "smtp.mail.me.com", 587, "starttls"),
    "me.com": ("imap.mail.me.com", 993, "smtp.mail.me.com", 587, "starttls"),
    "yahoo.com": ("imap.mail.yahoo.com", 993, "smtp.mail.yahoo.com", 465, "ssl"),
    "fastmail.com": ("imap.fastmail.com", 993, "smtp.fastmail.com", 465, "ssl"),
}
NO_LUNA = "Luna needs an AI model to do that. Add one in Settings, AI model."
HostName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255, pattern=r"^[A-Za-z0-9.-]+$")]
LOOPBACK = {"localhost", "127.0.0.1", "::1"}
# IMAP numbers, Gmail hex ids, Graph's long base64 ids: letters, digits, - _ =.
MessageUid = Annotated[str, Path(pattern=r"^[A-Za-z0-9_=-]{1,400}$")]


class AccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
    display_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    # Empty = the address. Servers: empty = the preset for that address.
    username: str = Field(default="", max_length=320)
    imap_host: HostName | None = None
    imap_port: int = Field(default=993, ge=1, le=65535)
    imap_security: Literal["ssl", "none"] = "ssl"
    smtp_host: HostName | None = None
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_security: Literal["ssl", "starttls", "none"] = "ssl"

    @field_validator("display_name")
    @classmethod
    def one_line(cls, value: str) -> str:
        if "\n" in value or "\r" in value:
            raise ValueError("The name must be one line")
        return value


class SendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: list[str] = Field(min_length=1, max_length=20)
    cc: list[str] = Field(default_factory=list, max_length=20)
    subject: str = Field(default="", max_length=300)
    body: str = Field(min_length=1, max_length=100_000)
    # Replying to this message in the inbox (keeps the thread).
    reply_to: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_=-]{1,400}$")


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tone: Literal["professional", "friendly", "short"] = "professional"
    # What the owner wants the reply to say, in their own words (optional).
    wish: str = Field(default="", max_length=1000)


class NewDraftRequest(DraftRequest):
    to: str = Field(default="", max_length=320)
    wish: str = Field(min_length=1, max_length=2000)


def account_json(account: EmailAccount) -> dict:
    # The password never leaves Core.
    return {
        "id": str(account.id),
        "address": account.address,
        "display_name": account.display_name,
        "kind": account.kind,
        "imap_host": account.imap_host or "",
        "smtp_host": account.smtp_host or "",
    }


def summary_json(item: MailSummary) -> dict:
    return {
        "uid": item.uid,
        "sender": item.sender,
        "sender_address": item.sender_address,
        "subject": item.subject,
        "date": item.date.isoformat() if item.date else None,
        "unread": item.unread,
    }


def message_json(message: MailMessage) -> dict:
    return {
        "uid": message.uid,
        "sender": message.sender,
        "sender_address": message.sender_address,
        "to": message.to,
        "cc": message.cc,
        "subject": message.subject,
        "date": message.date.isoformat() if message.date else None,
        "body": message.body,
        "html": message.html,
        "attachments": message.attachments,
    }


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


def backend_for(account: EmailAccount, secret_key: str, connectors: tuple, calendar: CalendarService):
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


def account_or_404(repository: EmailRepository, account_id: UUID) -> EmailAccount:
    account = repository.get(account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such email account")
    return account


def mail_problem(exc: MailError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.get("/accounts")
def list_accounts(repository: Annotated[EmailRepository, Depends(get_email_repository)]):
    return [account_json(account) for account in repository.list_all()]


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def add_account(
    body: AccountRequest,
    repository: Annotated[EmailRepository, Depends(get_email_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    connectors: Annotated[tuple, Depends(get_mail_connectors)],
):
    """Signs in once to check the app password works, then saves it encrypted."""
    domain = body.address.split("@")[-1].lower()
    preset = PRESETS.get(domain)
    imap_host = body.imap_host or (preset[0] if preset else None)
    smtp_host = body.smtp_host or (preset[2] if preset else None)
    if not imap_host or not smtp_host:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Venus doesn't know this provider's servers yet. Fill in the IMAP and SMTP servers.",
        )
    imap_port, smtp_port, smtp_security = body.imap_port, body.smtp_port, body.smtp_security
    if preset and not body.imap_host:
        imap_port, smtp_port, smtp_security = preset[1], preset[3], preset[4]
    # Unencrypted mail only to a test server on this same PC.
    if "none" in (body.imap_security, smtp_security) and not {imap_host, smtp_host} <= LOOPBACK:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Mail without encryption is only allowed to a test server on this PC.",
        )
    fields = {
        "address": body.address,
        "display_name": body.display_name,
        "kind": "imap",
        "imap_host": imap_host,
        "imap_port": imap_port,
        "imap_security": body.imap_security,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_security": smtp_security,
        "username": body.username.strip() or body.address,
    }
    check = MailSettings(password=body.password, **{k: v for k, v in fields.items() if k != "kind"})
    try:
        await asyncio.to_thread(mailbox.check_login, check, connectors[0])
    except MailError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    try:
        account = repository.add(
            datetime.now(timezone.utc), password_encrypted=encrypt_key(body.password, settings), **fields,
        )
    except DuplicateAccountError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That address is already added") from exc
    return account_json(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_account(account_id: UUID, repository: Annotated[EmailRepository, Depends(get_email_repository)]):
    if not repository.delete(account_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such email account")


@router.get("/accounts/{account_id}/messages")
async def list_messages(
    account_id: UUID,
    repository: Annotated[EmailRepository, Depends(get_email_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    connectors: Annotated[tuple, Depends(get_mail_connectors)],
    calendar: Annotated[CalendarService, Depends(get_calendar_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
):
    backend = backend_for(account_or_404(repository, account_id), settings.secret_key, connectors, calendar)
    try:
        found = await backend.inbox(limit)
    except MailError as exc:
        raise mail_problem(exc) from exc
    return [summary_json(item) for item in found]


async def fetch(backend, uid: str) -> MailMessage:
    try:
        return await backend.read(uid)
    except MailError as exc:
        raise mail_problem(exc) from exc


@router.get("/accounts/{account_id}/messages/{uid}")
async def open_message(
    account_id: UUID,
    uid: MessageUid,
    repository: Annotated[EmailRepository, Depends(get_email_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    connectors: Annotated[tuple, Depends(get_mail_connectors)],
    calendar: Annotated[CalendarService, Depends(get_calendar_service)],
):
    backend = backend_for(account_or_404(repository, account_id), settings.secret_key, connectors, calendar)
    return message_json(await fetch(backend, uid))


@router.post("/accounts/{account_id}/messages/{uid}/summary")
async def summarize_message(
    account_id: UUID,
    uid: MessageUid,
    repository: Annotated[EmailRepository, Depends(get_email_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    connectors: Annotated[tuple, Depends(get_mail_connectors)],
    provider: Annotated[ChatProvider, Depends(get_chat_provider)],
    calendar: Annotated[CalendarService, Depends(get_calendar_service)],
):
    backend = backend_for(account_or_404(repository, account_id), settings.secret_key, connectors, calendar)
    text = await assistant.summarize(provider, await fetch(backend, uid))
    if not text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_LUNA)
    return {"summary": text}


@router.post("/accounts/{account_id}/summary")
async def summarize_inbox(
    account_id: UUID,
    repository: Annotated[EmailRepository, Depends(get_email_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    connectors: Annotated[tuple, Depends(get_mail_connectors)],
    provider: Annotated[ChatProvider, Depends(get_chat_provider)],
    calendar: Annotated[CalendarService, Depends(get_calendar_service)],
):
    backend = backend_for(account_or_404(repository, account_id), settings.secret_key, connectors, calendar)
    try:
        found = await backend.inbox(30)
    except MailError as exc:
        raise mail_problem(exc) from exc
    if not found:
        return {"groups": []}
    text = await assistant.summarize_inbox(provider, found)
    if not text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_LUNA)
    groups = assistant.overview_groups(text, found)
    # If Luna didn't answer in the expected shape, show her words as they are.
    return {"groups": groups} if groups is not None else {"groups": [], "summary": text}


@router.post("/accounts/{account_id}/messages/{uid}/draft")
async def draft_reply(
    account_id: UUID,
    uid: MessageUid,
    body: DraftRequest,
    repository: Annotated[EmailRepository, Depends(get_email_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    connectors: Annotated[tuple, Depends(get_mail_connectors)],
    provider: Annotated[ChatProvider, Depends(get_chat_provider)],
    calendar: Annotated[CalendarService, Depends(get_calendar_service)],
):
    """Luna's reply, for the owner to read and change. Nothing is sent."""
    account = account_or_404(repository, account_id)
    message = await fetch(backend_for(account, settings.secret_key, connectors, calendar), uid)
    text = await assistant.draft_reply(provider, message, account.display_name, body.tone, body.wish)
    if not text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_LUNA)
    subject = message.subject if re.match(r"(?i)^re:", message.subject) else f"Re: {message.subject}"
    return {"to": [message.sender_address], "cc": [], "subject": subject, "body": text, "reply_to": uid}


@router.post("/accounts/{account_id}/draft")
async def draft_new(
    account_id: UUID,
    body: NewDraftRequest,
    repository: Annotated[EmailRepository, Depends(get_email_repository)],
    provider: Annotated[ChatProvider, Depends(get_chat_provider)],
):
    account = account_or_404(repository, account_id)
    text = await assistant.draft_new(provider, account.display_name, body.to, body.wish, body.tone)
    if not text:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_LUNA)
    return {"body": text}


@router.post("/accounts/{account_id}/send")
async def send_mail(
    account_id: UUID,
    body: SendRequest,
    repository: Annotated[EmailRepository, Depends(get_email_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    connectors: Annotated[tuple, Depends(get_mail_connectors)],
    calendar: Annotated[CalendarService, Depends(get_calendar_service)],
):
    """Only ever called by the owner's own Send button: Luna has no way to send."""
    backend = backend_for(account_or_404(repository, account_id), settings.secret_key, connectors, calendar)
    in_reply_to = references = thread_id = ""
    if body.reply_to:
        original = await fetch(backend, body.reply_to)
        in_reply_to, references, thread_id = original.message_id, original.references, original.thread_id
    outgoing = Outgoing(body.to, body.cc, body.subject, body.body, in_reply_to, references, thread_id)
    try:
        await backend.send(outgoing)
    except MailError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    return {"sent": True}
