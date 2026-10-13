"""Reading mail over IMAP and sending it over SMTP (Python's own imaplib and smtplib).

Works with any provider that gives an "app password": Gmail, iCloud, Yahoo,
Fastmail and most others. Each call opens its own connection and closes it,
so nothing stays logged in between requests. The libraries block, so the
router runs these in a thread.
"""

import email
import imaplib
import re
import smtplib
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from email.policy import default as default_policy
from email.utils import formataddr, formatdate, getaddresses, make_msgid, parseaddr, parsedate_to_datetime
from html.parser import HTMLParser

TIMEOUT = 20
# The email body Luna reads at most (long newsletters cost money for nothing).
MAX_BODY = 20_000
# Bigger HTML than this is shown as text only (it's almost always a newsletter).
MAX_HTML = 500_000


class MailError(Exception):
    """The mail server said no or couldn't be reached; the message is for the page."""


@dataclass(frozen=True)
class MailSettings:
    address: str
    display_name: str
    imap_host: str
    imap_port: int
    imap_security: str  # ssl or none
    smtp_host: str
    smtp_port: int
    smtp_security: str  # ssl, starttls or none
    username: str
    password: str


@dataclass(frozen=True)
class MailSummary:
    uid: str
    sender: str
    sender_address: str
    subject: str
    date: datetime | None
    unread: bool


@dataclass(frozen=True)
class MailMessage:
    uid: str
    sender: str
    sender_address: str
    to: list[str]
    cc: list[str]
    subject: str
    date: datetime | None
    body: str
    message_id: str
    references: str
    attachments: list[str] = field(default_factory=list)
    # Gmail's conversation id, so a reply stays in the same thread there.
    thread_id: str = ""
    # The HTML version, for the page to show (cleaned there, images only on request).
    html: str = ""


@dataclass(frozen=True)
class Outgoing:
    to: list[str]
    cc: list[str]
    subject: str
    body: str
    # Replying: the original's Message-ID and References, so it stays in the thread.
    in_reply_to: str = ""
    references: str = ""
    thread_id: str = ""


# --- HTML mail as plain text ------------------------------------------------


class _Text(HTMLParser):
    BLOCKS = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "table", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head"):
            self.skip += 1
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head") and self.skip:
            self.skip -= 1
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """Only the words: Venus never shows a sender's HTML (no tracking pixels, no scripts)."""
    parser = _Text()
    parser.feed(html)
    text = "".join(parser.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()


# --- Connections --------------------------------------------------------------


def open_imap(settings: MailSettings) -> imaplib.IMAP4:
    if settings.imap_security == "none":
        return imaplib.IMAP4(settings.imap_host, settings.imap_port, timeout=TIMEOUT)
    return imaplib.IMAP4_SSL(
        settings.imap_host, settings.imap_port, ssl_context=ssl.create_default_context(), timeout=TIMEOUT,
    )


def open_smtp(settings: MailSettings) -> smtplib.SMTP:
    if settings.smtp_security == "ssl":
        return smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ssl.create_default_context(), timeout=TIMEOUT)
    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=TIMEOUT)
    if settings.smtp_security == "starttls":
        server.starttls(context=ssl.create_default_context())
    return server


def signed_in(settings: MailSettings, connect=open_imap) -> imaplib.IMAP4:
    try:
        imap = connect(settings)
    except (OSError, imaplib.IMAP4.error) as exc:
        raise MailError(f"Couldn't reach {settings.imap_host}. Check the server name and port.") from exc
    try:
        imap.login(settings.username, settings.password)
    except imaplib.IMAP4.error as exc:
        close(imap)
        raise MailError(
            "The mail server didn't accept the login. Use an app password (not your normal password)."
        ) from exc
    return imap


def close(imap) -> None:
    try:
        imap.logout()
    except Exception:
        pass


def check_login(settings: MailSettings, connect=open_imap) -> None:
    """Used when adding an account: signs in and opens the inbox once."""
    imap = signed_in(settings, connect)
    try:
        status, _ = imap.select("INBOX", readonly=True)
        if status != "OK":
            raise MailError("Signed in, but the inbox couldn't be opened.")
    finally:
        close(imap)


# --- Reading ------------------------------------------------------------------


def decoded(value) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()


def sender_of(message) -> tuple[str, str]:
    name, address = parseaddr(decoded(message.get("From")))
    return (name or address), address


def date_of(message) -> datetime | None:
    try:
        moment = parsedate_to_datetime(decoded(message.get("Date")))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def arrived(meta: str) -> datetime | None:
    """When the server got it (INTERNALDATE), for mail without a Date header."""
    parsed = imaplib.Internaldate2tuple(meta.encode())
    return datetime.fromtimestamp(time.mktime(parsed)).astimezone(timezone.utc) if parsed else None


def inbox(settings: MailSettings, limit: int = 30, connect=open_imap) -> list[MailSummary]:
    """The newest messages in the inbox, newest first. Doesn't mark anything read."""
    imap = signed_in(settings, connect)
    try:
        imap.select("INBOX", readonly=True)
        status, data = imap.uid("SEARCH", None, "ALL")
        if status != "OK":
            raise MailError("The inbox couldn't be searched.")
        uids = (data[0] or b"").split()[-limit:]
        if not uids:
            return []
        status, data = imap.uid(
            "FETCH", b",".join(uids).decode(), "(UID FLAGS INTERNALDATE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])",
        )
        if status != "OK":
            raise MailError("The inbox couldn't be read.")
    finally:
        close(imap)
    found: dict[str, MailSummary] = {}
    current: tuple[str, bytes, str] | None = None

    def keep() -> None:
        if current is None:
            return
        uid, header, flags = current
        message = email.message_from_bytes(header, policy=default_policy)
        name, address = sender_of(message)
        found[uid] = MailSummary(
            uid, name, address, decoded(message.get("Subject")) or "(no subject)",
            date_of(message) or arrived(flags), "\\Seen" not in flags,
        )

    for part in data:
        # A message comes as (b'5 (UID 12 FLAGS (\\Seen) BODY[...] {123}', b'<headers>'),
        # and some servers send FLAGS after the headers, in the next b' FLAGS (...))'.
        if isinstance(part, tuple):
            keep()
            meta = part[0].decode(errors="replace")
            uid = re.search(r"UID (\d+)", meta)
            current = (uid.group(1), part[1], meta) if uid else None
        elif isinstance(part, bytes) and current is not None and b"FLAGS" in part:
            current = (current[0], current[1], current[2] + part.decode(errors="replace"))
    keep()
    return sorted(found.values(), key=lambda summary: int(summary.uid), reverse=True)


def check_uid(uid: str) -> str:
    if not uid.isdigit():
        raise MailError("That isn't a message id.")
    return uid


def read(settings: MailSettings, uid: str, connect=open_imap) -> MailMessage:
    """One whole message as text. Opening it marks it read, like any mail app."""
    uid = check_uid(uid)
    imap = signed_in(settings, connect)
    try:
        imap.select("INBOX")
        status, data = imap.uid("FETCH", uid, "(BODY.PEEK[])")
        raw = next((part[1] for part in data if isinstance(part, tuple)), None) if status == "OK" else None
        if raw is None:
            raise MailError("That message isn't in the inbox anymore.")
        imap.uid("STORE", uid, "+FLAGS", "(\\Seen)")
    finally:
        close(imap)
    return parse_message(uid, raw)


def parse_message(uid: str, raw: bytes, thread_id: str = "") -> MailMessage:
    """A whole raw message (RFC 822) as Venus shows it: plain text, attachments by name."""
    message = email.message_from_bytes(raw, policy=default_policy)
    part = message.get_body(preferencelist=("plain", "html"))
    body = ""
    if part is not None:
        content = part.get_content()
        body = html_to_text(content) if part.get_content_type() == "text/html" else content
    html_part = message.get_body(preferencelist=("html",))
    html = html_part.get_content() if html_part is not None else ""
    name, address = sender_of(message)
    return MailMessage(
        uid=uid,
        sender=name,
        sender_address=address,
        to=[addr for _, addr in getaddresses([decoded(message.get("To"))]) if addr],
        cc=[addr for _, addr in getaddresses([decoded(message.get("Cc"))]) if addr],
        subject=decoded(message.get("Subject")) or "(no subject)",
        date=date_of(message),
        body=body.strip()[:200_000],
        message_id=decoded(message.get("Message-ID")),
        references=decoded(message.get("References")),
        attachments=[decoded(item.get_filename()) or "attachment" for item in message.iter_attachments()],
        thread_id=thread_id,
        html=html if len(html) <= MAX_HTML else "",
    )


# --- Sending ------------------------------------------------------------------


def clean_addresses(values: list[str]) -> list[str]:
    """Plain addresses only: no names with commas or line breaks (header injection)."""
    addresses = []
    for value in values:
        value = value.strip()
        if not value:
            continue
        if "\n" in value or "\r" in value or not re.fullmatch(r"[^@\s<>,;\"]+@[^@\s<>,;\"]+\.[^@\s<>,;\"]+", value):
            raise MailError(f"{value[:80]} isn't an email address.")
        addresses.append(value)
    return addresses


def build(settings: MailSettings, outgoing: Outgoing) -> EmailMessage:
    to = clean_addresses(outgoing.to)
    cc = clean_addresses(outgoing.cc)
    if not to:
        raise MailError("Add at least one address to send to.")
    message = EmailMessage()
    message["From"] = formataddr((settings.display_name, settings.address))
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = decoded(outgoing.subject)[:300]
    message["Date"] = formatdate()
    message["Message-ID"] = make_msgid(domain=settings.address.split("@")[-1])
    if outgoing.in_reply_to:
        message["In-Reply-To"] = decoded(outgoing.in_reply_to)
        message["References"] = f"{decoded(outgoing.references)} {decoded(outgoing.in_reply_to)}".strip()
    message.set_content(outgoing.body)
    return message


def send(settings: MailSettings, outgoing: Outgoing, connect=open_smtp) -> None:
    message = build(settings, outgoing)
    try:
        server = connect(settings)
    except OSError as exc:
        raise MailError(f"Couldn't reach {settings.smtp_host} to send.") from exc
    try:
        server.login(settings.username, settings.password)
        server.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise MailError("The mail server didn't accept the login for sending.") from exc
    except smtplib.SMTPException as exc:
        raise MailError("The mail server didn't send it.") from exc
    finally:
        try:
            server.quit()
        except Exception:
            pass
