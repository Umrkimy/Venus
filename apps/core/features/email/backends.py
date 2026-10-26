"""One way to reach each kind of mailbox: IMAP/SMTP, Gmail's API, or Microsoft Graph.

All three hand back the same MailSummary / MailMessage, and all three send the
same MIME message Venus builds, so the page and Luna never care which it is.
Gmail and Graph get the raw message (RFC 822) and Venus parses it itself,
the same as IMAP: one parser, one way of showing mail as plain text.
"""

import asyncio
import base64
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

import httpx2

from features.email import mailbox
from features.email.mailbox import MailError, MailMessage, MailSettings, MailSummary, Outgoing

AccessToken = Callable[[], Awaitable[str]]


class ImapBackend:
    def __init__(self, settings: MailSettings, open_imap, open_smtp) -> None:
        self.settings = settings
        self.open_imap = open_imap
        self.open_smtp = open_smtp

    async def inbox(self, limit: int) -> list[MailSummary]:
        return await asyncio.to_thread(mailbox.inbox, self.settings, limit, self.open_imap)

    async def read(self, uid: str) -> MailMessage:
        return await asyncio.to_thread(mailbox.read, self.settings, uid, self.open_imap)

    async def send(self, outgoing: Outgoing) -> None:
        await asyncio.to_thread(mailbox.send, self.settings, outgoing, self.open_smtp)


class _HttpBackend:
    label = ""

    def __init__(self, settings: MailSettings, access_token: AccessToken, transport: httpx2.AsyncBaseTransport | None = None) -> None:
        self.settings = settings
        self.access_token = access_token
        self.transport = transport

    async def call(self, method: str, url: str, **options) -> httpx2.Response:
        token = await self.access_token()
        headers = {"Authorization": f"Bearer {token}", **options.pop("headers", {})}
        try:
            async with httpx2.AsyncClient(transport=self.transport, timeout=20) as client:
                response = await client.request(method, url, headers=headers, **options)
        except httpx2.HTTPError as exc:
            raise MailError(f"Couldn't reach {self.label}.") from exc
        if response.status_code in (401, 403):
            raise MailError(
                f"{self.label} didn't allow that. Connect it again in Settings, Email "
                "(your uni may need to approve Venus first)."
            )
        if response.status_code == 404:
            raise MailError("That message isn't there anymore.")
        if response.status_code >= 300:
            raise MailError(f"{self.label} answered HTTP {response.status_code}.")
        return response


class GmailBackend(_HttpBackend):
    label = "Gmail"
    api = "https://gmail.googleapis.com/gmail/v1/users/me"

    async def inbox(self, limit: int) -> list[MailSummary]:
        listing = (await self.call("GET", f"{self.api}/messages", params={"labelIds": "INBOX", "maxResults": str(limit)})).json()
        ids = [item["id"] for item in listing.get("messages", [])]

        async def one(message_id: str) -> MailSummary:
            item = (await self.call(
                "GET", f"{self.api}/messages/{message_id}",
                params=[("format", "metadata"), ("metadataHeaders", "From"), ("metadataHeaders", "Subject"),
                        ("metadataHeaders", "List-Unsubscribe")],
            )).json()
            headers = {h["name"].lower(): h["value"] for h in item.get("payload", {}).get("headers", [])}
            name, address = mailbox.parseaddr(mailbox.decoded(headers.get("from")))
            received = datetime.fromtimestamp(int(item.get("internalDate", "0")) / 1000, tz=timezone.utc)
            labels = item.get("labelIds", [])
            return MailSummary(
                message_id, name or address, address, mailbox.decoded(headers.get("subject")) or "(no subject)",
                received, "UNREAD" in labels, mailbox.categorize("list-unsubscribe" in headers, labels),
            )

        return list(await asyncio.gather(*(one(message_id) for message_id in ids)))

    async def read(self, uid: str) -> MailMessage:
        item = (await self.call("GET", f"{self.api}/messages/{uid}", params={"format": "raw"})).json()
        raw = base64.urlsafe_b64decode(item["raw"] + "=" * (-len(item["raw"]) % 4))
        if "UNREAD" in item.get("labelIds", []):
            await self.call("POST", f"{self.api}/messages/{uid}/modify", json={"removeLabelIds": ["UNREAD"]})
        return mailbox.parse_message(uid, raw, thread_id=item.get("threadId", ""))

    async def send(self, outgoing: Outgoing) -> None:
        raw = base64.urlsafe_b64encode(mailbox.build(self.settings, outgoing).as_bytes()).decode()
        body = {"raw": raw} | ({"threadId": outgoing.thread_id} if outgoing.thread_id else {})
        await self.call("POST", f"{self.api}/messages/send", json=body)


class GraphBackend(_HttpBackend):
    label = "Outlook"
    api = "https://graph.microsoft.com/v1.0/me"

    async def inbox(self, limit: int) -> list[MailSummary]:
        listing = (await self.call("GET", f"{self.api}/mailFolders/inbox/messages", params={
            "$top": str(limit),
            "$select": "id,subject,from,receivedDateTime,isRead,inferenceClassification,internetMessageHeaders",
            "$orderby": "receivedDateTime desc",
        })).json()
        found = []
        for item in listing.get("value", []):
            sender = (item.get("from") or {}).get("emailAddress") or {}
            received = item.get("receivedDateTime")
            headers = {(h.get("name") or "").lower() for h in item.get("internetMessageHeaders") or []}
            found.append(MailSummary(
                item["id"],
                sender.get("name") or sender.get("address") or "",
                sender.get("address") or "",
                item.get("subject") or "(no subject)",
                datetime.fromisoformat(received.replace("Z", "+00:00")) if received else None,
                not item.get("isRead", True),
                mailbox.categorize("list-unsubscribe" in headers, focused=item.get("inferenceClassification") != "other"),
            ))
        return found

    async def read(self, uid: str) -> MailMessage:
        raw = (await self.call("GET", f"{self.api}/messages/{uid}/$value")).content
        await self.call("PATCH", f"{self.api}/messages/{uid}", json={"isRead": True})
        return mailbox.parse_message(uid, raw)

    async def send(self, outgoing: Outgoing) -> None:
        # Graph takes the whole MIME message, base64, as text: our own headers and threading stay.
        mime = base64.b64encode(mailbox.build(self.settings, outgoing).as_bytes())
        await self.call("POST", f"{self.api}/sendMail", content=mime, headers={"Content-Type": "text/plain"})
