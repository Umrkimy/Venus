import asyncio
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from config import CoreSettings, get_settings
from features.auth.dependencies import require_owner
from features.email import mailbox
from features.email.dependencies import MailBackend, get_email_repository, get_mail_backend, get_mail_connectors
from features.email.mailbox import MailError, MailMessage, MailSettings, Outgoing
from features.email.repository import DuplicateAccountError, EmailRepository
from features.email.schemas import AccountRequest, MessageUid, SendRequest, account_json, message_json, summary_json
from features.settings.router import encrypt_key

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
LOOPBACK = {"localhost", "127.0.0.1", "::1"}


def mail_problem(exc: MailError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


async def fetch(backend, uid: str) -> MailMessage:
    try:
        return await backend.read(uid)
    except MailError as exc:
        raise mail_problem(exc) from exc


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
async def list_messages(backend: Annotated[MailBackend, Depends(get_mail_backend)], limit: Annotated[int, Query(ge=1, le=100)] = 30):
    try:
        found = await backend.inbox(limit)
    except MailError as exc:
        raise mail_problem(exc) from exc
    return [summary_json(item) for item in found]


@router.get("/accounts/{account_id}/messages/{uid}")
async def open_message(uid: MessageUid, backend: Annotated[MailBackend, Depends(get_mail_backend)]):
    return message_json(await fetch(backend, uid))


@router.post("/accounts/{account_id}/send")
async def send_mail(body: SendRequest, backend: Annotated[MailBackend, Depends(get_mail_backend)]):
    """Only ever called by the owner's own Send button: Luna has no way to send."""
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
