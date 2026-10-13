"""Mail through the Google or Microsoft sign-in (uni Microsoft 365, Gmail without an app password)."""

import base64
import json
from email import message_from_bytes
from email.policy import default as default_policy
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from cryptography.fernet import Fernet
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.calendar.dependencies import get_calendar_repository, get_calendar_service, get_sign_ins
from features.calendar.repository import CalendarRepository
from features.calendar.service import Cached, CalendarService, SignIns
from features.chat.dependencies import get_chat_provider
from features.email.dependencies import get_email_repository
from features.email.repository import EmailRepository
from features.settings.secrets import encrypt_text
from main import app
from tests.database import make_test_engine

SECRET = Fernet.generate_key().decode()
OWNER = {"Authorization": "Bearer test-owner-token"}
RAW = (
    b"From: Dr. Aina <aina@uni.edu.my>\r\nTo: umar@student.uni.edu.my\r\nSubject: Viva slot\r\n"
    b"Message-ID: <viva@uni.edu.my>\r\nDate: Wed, 14 Oct 2026 08:00:00 +0800\r\n\r\nCan you do Thursday 10am?\r\n"
)


class FakeCloud:
    """Google and Microsoft: tokens, Gmail and Graph mail."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        url = str(request.url)
        if "oauth2.googleapis.com/token" in url:
            return httpx2.Response(200, json={"access_token": "g-access", "refresh_token": "g-refresh"})
        if "login.microsoftonline.com" in url:
            return httpx2.Response(200, json={"access_token": "m-access", "refresh_token": "m-refresh"})
        if "calendarList" in url:
            return httpx2.Response(200, json={"items": [{"id": "umar@gmail.com", "primary": True}]})
        if url.endswith("/me?%24select=mail%2CuserPrincipalName") or "/v1.0/me?" in url:
            return httpx2.Response(200, json={"mail": "umar@student.uni.edu.my"})
        gmail = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        if url.startswith(f"{gmail}?"):
            return httpx2.Response(200, json={"messages": [{"id": "18f1a"}, {"id": "18f1b"}]})
        if url.startswith(f"{gmail}/18f1a?format=metadata") or url.startswith(f"{gmail}/18f1b?format=metadata"):
            message_id = url.split("/")[-1].split("?")[0]
            return httpx2.Response(200, json={
                "id": message_id, "labelIds": ["INBOX"] + (["UNREAD"] if message_id == "18f1a" else []),
                "internalDate": "1792368000000",
                "payload": {"headers": [{"name": "From", "value": "Dr. Aina <aina@uni.edu.my>"}, {"name": "Subject", "value": f"Mail {message_id}"}]},
            })
        if url.startswith(f"{gmail}/18f1a?format=raw"):
            return httpx2.Response(200, json={"id": "18f1a", "threadId": "t-77", "labelIds": ["UNREAD"],
                                              "raw": base64.urlsafe_b64encode(RAW).decode().rstrip("=")})
        if url in (f"{gmail}/18f1a/modify", f"{gmail}/send"):
            return httpx2.Response(200, json={"id": "sent-1"})
        graph = "https://graph.microsoft.com/v1.0/me"
        if url.startswith(f"{graph}/mailFolders/inbox/messages"):
            return httpx2.Response(200, json={"value": [{"id": "AAMk-1=", "subject": "Viva slot", "isRead": False,
                "receivedDateTime": "2026-10-14T00:00:00Z", "from": {"emailAddress": {"name": "Dr. Aina", "address": "aina@uni.edu.my"}}}]})
        if url == f"{graph}/messages/AAMk-1=/$value":
            return httpx2.Response(200, content=RAW)
        if url == f"{graph}/messages/AAMk-1=" and request.method == "PATCH":
            return httpx2.Response(200, json={})
        if url == f"{graph}/sendMail":
            return httpx2.Response(202)
        return httpx2.Response(404)


@pytest.fixture
def cloud():
    return FakeCloud()


@pytest.fixture
def setup(cloud):
    engine = make_test_engine()
    calendars = CalendarRepository(engine)
    emails = EmailRepository(engine)
    sign_ins = SignIns()
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token", dev_owner_token="test-owner-token",
        database_url="sqlite+pysqlite:///:memory:", secret_key=SECRET,
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_calendar_repository] = lambda: calendars
    app.dependency_overrides[get_email_repository] = lambda: emails
    app.dependency_overrides[get_sign_ins] = lambda: sign_ins
    app.dependency_overrides[get_calendar_service] = lambda: CalendarService(calendars, SECRET, httpx2.MockTransport(cloud), Cached())
    app.dependency_overrides[get_chat_provider] = lambda: None
    yield calendars, emails
    app.dependency_overrides.clear()
    engine.dispose()


client = TestClient(app, follow_redirects=False)


def save_app(calendars: CalendarRepository, provider: str) -> None:
    calendars.save_client(provider, f"{provider}-client", encrypt_text(f"{provider}-secret", SECRET))


def sign_in(provider: str, name: str = "Umar Hakimi") -> str:
    """Connect with mail; returns where Venus sends the browser back to."""
    started = client.get(f"/calendar/{provider}/connect", params={"mail": "true", "name": name}, headers=OWNER)
    assert started.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    state = parse_qs(urlsplit(started.headers["location"]).query)["state"][0]
    done = client.get(f"/calendar/{provider}/callback", params={"state": state, "code": "c0de"}, headers=OWNER)
    return done.headers["location"]


@pytest.mark.parametrize(
    ("provider", "scope_has"),
    [
        ("google", "https://www.googleapis.com/auth/gmail.modify"),
        ("microsoft", "Mail.ReadWrite Mail.Send"),
    ],
)
def test_connect_with_mail_asks_for_mail_too(setup, provider, scope_has):
    save_app(setup[0], provider)

    started = client.get(f"/calendar/{provider}/connect", params={"mail": "true"}, headers=OWNER)

    query = parse_qs(urlsplit(started.headers["location"]).query)
    assert scope_has in query["scope"][0]
    assert ("calendar" in query["scope"][0].lower())  # The calendar permission stays.


def test_microsoft_sign_in_adds_the_uni_mailbox(setup, cloud: FakeCloud):
    calendars, emails = setup
    save_app(calendars, "microsoft")

    back = sign_in("microsoft")

    assert back == "/settings/email?connected=microsoft"
    [account] = emails.list_all()
    assert (account.kind, account.address, account.display_name, account.password_encrypted) == (
        "microsoft", "umar@student.uni.edu.my", "Umar Hakimi", None,
    )
    assert calendars.get("microsoft").mail is True
    # The token exchange asked for mail as well (Microsoft wants scopes there too).
    token_form = parse_qs(cloud.requests[0].content.decode())
    assert "Mail.Send" in token_form["scope"][0]


def test_reconnecting_the_calendar_keeps_mail(setup):
    calendars, _ = setup
    save_app(calendars, "google")
    sign_in("google")

    started = client.get("/calendar/google/connect", headers=OWNER)

    assert "gmail.modify" in parse_qs(urlsplit(started.headers["location"]).query)["scope"][0]


def test_no_app_saved_yet_says_where(setup):
    started = client.get("/calendar/google/connect", params={"mail": "true"}, headers=OWNER)

    assert started.headers["location"].startswith("/settings/email?error=")


def test_disconnect_removes_its_mailbox(setup):
    calendars, emails = setup
    save_app(calendars, "google")
    sign_in("google")

    assert client.delete("/calendar/google", headers=OWNER).status_code == status.HTTP_204_NO_CONTENT
    assert emails.list_all() == []


def test_gmail_inbox_read_and_reply_in_thread(setup, cloud: FakeCloud):
    calendars, emails = setup
    save_app(calendars, "google")
    sign_in("google")
    account = emails.list_all()[0].id

    inbox = client.get(f"/email/accounts/{account}/messages", headers=OWNER).json()
    opened = client.get(f"/email/accounts/{account}/messages/18f1a", headers=OWNER).json()
    sent = client.post(f"/email/accounts/{account}/send", json={
        "to": ["aina@uni.edu.my"], "subject": "Re: Viva slot", "body": "Thursday 10am works.", "reply_to": "18f1a",
    }, headers=OWNER)

    assert [(m["uid"], m["unread"]) for m in inbox] == [("18f1a", True), ("18f1b", False)]
    assert opened["body"] == "Can you do Thursday 10am?"
    assert sent.json() == {"sent": True}
    marked = next(r for r in cloud.requests if str(r.url).endswith("/18f1a/modify"))
    assert json.loads(marked.content) == {"removeLabelIds": ["UNREAD"]}
    send = next(r for r in cloud.requests if str(r.url).endswith("/messages/send"))
    body = json.loads(send.content)
    assert body["threadId"] == "t-77"
    mime = message_from_bytes(base64.urlsafe_b64decode(body["raw"]), policy=default_policy)
    assert mime["In-Reply-To"] == "<viva@uni.edu.my>"
    assert mime["From"] == "Umar Hakimi <umar@gmail.com>"
    assert send.headers["Authorization"] == "Bearer g-access"


def test_outlook_inbox_read_and_send(setup, cloud: FakeCloud):
    calendars, emails = setup
    save_app(calendars, "microsoft")
    sign_in("microsoft")
    account = emails.list_all()[0].id

    inbox = client.get(f"/email/accounts/{account}/messages", headers=OWNER).json()
    opened = client.get(f"/email/accounts/{account}/messages/AAMk-1=", headers=OWNER).json()
    sent = client.post(f"/email/accounts/{account}/send", json={
        "to": ["aina@uni.edu.my"], "subject": "Re: Viva slot", "body": "Yes, Thursday works.", "reply_to": "AAMk-1=",
    }, headers=OWNER)

    assert inbox == [{"uid": "AAMk-1=", "sender": "Dr. Aina", "sender_address": "aina@uni.edu.my",
                      "subject": "Viva slot", "date": "2026-10-14T00:00:00+00:00", "unread": True}]
    assert opened["sender_address"] == "aina@uni.edu.my"
    assert sent.json() == {"sent": True}
    send = next(r for r in cloud.requests if str(r.url).endswith("/sendMail"))
    mime = message_from_bytes(base64.b64decode(send.content), policy=default_policy)
    assert mime["To"] == "aina@uni.edu.my" and mime["In-Reply-To"] == "<viva@uni.edu.my>"
    # Microsoft's refresh asked for mail too, or the token couldn't read mail.
    refresh = [parse_qs(r.content.decode()) for r in cloud.requests if "login.microsoftonline.com" in str(r.url)]
    assert all("Mail.ReadWrite" in form["scope"][0] for form in refresh)


def test_mail_blocked_by_the_uni_says_so(setup, cloud: FakeCloud):
    calendars, emails = setup
    save_app(calendars, "microsoft")
    sign_in("microsoft")
    account = emails.list_all()[0].id
    cloud.__class__ = type("Blocked", (FakeCloud,), {
        "__call__": lambda self, r: httpx2.Response(403) if "graph.microsoft.com" in str(r.url) else FakeCloud.__call__(self, r),
    })

    response = client.get(f"/email/accounts/{account}/messages", headers=OWNER)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert "your uni may need to approve Venus" in response.json()["detail"]
