from typing import Annotated, Literal

from fastapi import Path
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from features.email.mailbox import MailMessage, MailSummary
from features.email.models.email_account import EmailAccount

HostName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255, pattern=r"^[A-Za-z0-9.-]+$")]
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
        "category": item.category,
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
