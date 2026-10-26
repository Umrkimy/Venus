import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

import httpx2
import pytest
from cryptography.fernet import Fernet
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.calendar.dependencies import get_calendar_repository, get_calendar_service, get_sign_ins
from features.calendar.providers import Event, Google, Microsoft
from features.calendar.repository import CalendarRepository
from features.email.dependencies import get_email_repository
from features.email.repository import EmailRepository
from features.calendar.service import (
    Cached,
    CalendarService,
    SignIns,
    calendar_lines,
    due_soon,
    first_today_line,
)
from features.settings.secrets import decrypt_text, encrypt_text
from main import app
from tests.database import make_test_engine

SECRET = Fernet.generate_key().decode()
OWNER = {"Authorization": "Bearer test-owner-token"}
NODE = {"Authorization": "Bearer test-node-token"}
NOW = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)  # 09:00 in Kuala Lumpur
KL = ZoneInfo("Asia/Kuala_Lumpur")


class FakeProviders:
    """Google's and Microsoft's servers, as far as Venus talks to them."""

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []
        self.fail_google = False

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        url = str(request.url)
        if "oauth2.googleapis.com/token" in url:
            if self.fail_google:
                return httpx2.Response(400, json={"error": "invalid_grant"})
            return httpx2.Response(200, json={"access_token": "g-access", "refresh_token": "g-refresh"})
        if "login.microsoftonline.com" in url:
            # Microsoft rotates the refresh token every time.
            return httpx2.Response(200, json={"access_token": "m-access", "refresh_token": "m-refresh-new"})
        if url.startswith("https://www.googleapis.com/calendar/v3/users/me/calendarList"):
            return httpx2.Response(200, json={"items": [
                {"id": "me@gmail.com", "primary": True},
                {"id": "classes@group", "selected": True},
                {"id": "hidden@group", "selected": False},
            ]})
        if "/calendars/me%40gmail.com/events" in url or "/calendars/me@gmail.com/events" in url:
            return httpx2.Response(200, json={"items": [
                {"id": "a", "summary": "Gym", "start": {"dateTime": "2026-10-14T10:00:00+08:00"},
                 "end": {"dateTime": "2026-10-14T11:00:00+08:00"}},
                {"id": "b", "summary": "Gone", "status": "cancelled", "start": {"dateTime": "2026-10-14T12:00:00+08:00"},
                 "end": {"dateTime": "2026-10-14T13:00:00+08:00"}},
                {"id": "c", "summary": "Holiday", "start": {"date": "2026-10-16"}, "end": {"date": "2026-10-17"}},
            ]})
        if "/calendars/classes%40group/events" in url or "/calendars/classes@group/events" in url:
            return httpx2.Response(200, json={"items": [
                {"id": "d", "summary": "Database class", "location": "Room 3",
                 "start": {"dateTime": "2026-10-14T01:05:00Z"}, "end": {"dateTime": "2026-10-14T03:00:00Z"}},
            ]})
        if "graph.microsoft.com/v1.0/me/calendarView" in url:
            return httpx2.Response(200, json={"value": [
                {"id": "x", "subject": "Lecturer meeting", "isAllDay": False, "isCancelled": False,
                 "start": {"dateTime": "2026-10-15T06:00:00.0000000"}, "end": {"dateTime": "2026-10-15T07:00:00.0000000"},
                 "location": {"displayName": "Teams"}},
            ]})
        if "graph.microsoft.com/v1.0/me" in url:
            return httpx2.Response(200, json={"mail": "me@uni.edu"})
        return httpx2.Response(404)


@pytest.fixture
def fake():
    return FakeProviders()


@pytest.fixture
def repository():
    engine = make_test_engine()
    yield CalendarRepository(engine)
    engine.dispose()


def connect_both(repository: CalendarRepository):
    for name, token in (("google", "g-refresh"), ("microsoft", "m-refresh")):
        repository.save_client(name, f"{name}-client", encrypt_text(f"{name}-secret", SECRET))
        repository.connect(name, encrypt_text(token, SECRET), None, NOW)


def test_events_from_every_shown_calendar_sorted_without_cancelled(repository, fake):
    connect_both(repository)
    service = CalendarService(repository, SECRET, httpx2.MockTransport(fake), Cached())

    events, errors = asyncio.run(service.events(NOW))

    assert errors == []
    assert [e.title for e in events] == ["Database class", "Gym", "Lecturer meeting", "Holiday"]
    assert events[0].location == "Room 3" and events[0].source == "Google"
    assert events[3].all_day is True
    # The calendar unticked in Google Calendar is not read.
    assert not any("hidden" in str(r.url) for r in fake.requests)


def test_microsofts_new_refresh_token_is_kept(repository, fake):
    connect_both(repository)
    service = CalendarService(repository, SECRET, httpx2.MockTransport(fake), Cached())

    asyncio.run(service.events(NOW))

    saved = repository.get("microsoft").refresh_token_encrypted
    assert decrypt_text(saved, SECRET) == "m-refresh-new"


def test_one_broken_calendar_doesnt_hide_the_other(repository, fake):
    connect_both(repository)
    fake.fail_google = True
    service = CalendarService(repository, SECRET, httpx2.MockTransport(fake), Cached())

    events, errors = asyncio.run(service.events(NOW))

    assert [e.title for e in events] == ["Lecturer meeting"]
    assert errors == ["Google signed Venus out. Press Reconnect to sign in again."]


def test_signed_out_is_remembered_and_google_isnt_asked_again(repository, fake):
    connect_both(repository)
    fake.fail_google = True
    service = CalendarService(repository, SECRET, httpx2.MockTransport(fake), Cached())

    asyncio.run(service.between(NOW, NOW + timedelta(days=1)))
    asked = len([r for r in fake.requests if "oauth2.googleapis.com" in str(r.url)])
    _, errors = asyncio.run(service.between(NOW, NOW + timedelta(days=1)))

    assert repository.get("google").signed_out_at is not None
    assert repository.get("microsoft").signed_out_at is None
    assert len([r for r in fake.requests if "oauth2.googleapis.com" in str(r.url)]) == asked == 1
    assert errors == ["Google signed Venus out. Press Reconnect to sign in again."]


def test_settings_shows_signed_out_and_signing_in_again_clears_it(client, repository, fake):
    client.put("/calendar/google", json={"client_id": "g-client", "client_secret": "s3cret"}, headers=OWNER)
    repository.connect("google", encrypt_text("old", SECRET), "me@gmail.com", NOW)
    repository.mark_signed_out("google", NOW)

    listed = next(c for c in client.get("/calendar", headers=OWNER).json() if c["provider"] == "google")
    start = client.get("/calendar/google/connect", headers=OWNER, follow_redirects=False)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    client.get(f"/calendar/google/callback?state={state}&code=c0de", headers=OWNER, follow_redirects=False)
    again = next(c for c in client.get("/calendar", headers=OWNER).json() if c["provider"] == "google")

    assert (listed["connected"], listed["signed_out_at"]) == (False, NOW.isoformat())
    assert (again["connected"], again["signed_out_at"]) == (True, None)


@pytest.mark.parametrize(("back", "page"), [("email", "/email"), ("calendar", "/calendar"), ("home", "/")])
def test_reconnect_on_a_page_comes_back_to_that_page(client, repository, fake, back, page):
    client.put("/calendar/google", json={"client_id": "g-client", "client_secret": "s3cret"}, headers=OWNER)
    repository.connect("google", encrypt_text("old", SECRET), "me@gmail.com", NOW)
    repository.mark_signed_out("google", NOW)

    listed = client.get("/calendar/events", headers=OWNER).json()
    start = client.get(f"/calendar/google/connect?back={back}", headers=OWNER, follow_redirects=False)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    done = client.get(f"/calendar/google/callback?state={state}&code=c0de", headers=OWNER, follow_redirects=False)

    assert listed["signed_out"] == ["google"]
    assert done.headers["location"] == f"{page}?connected=google"
    assert client.get("/calendar/events", headers=OWNER).json()["signed_out"] == []


def test_reconnect_only_goes_back_to_venus_pages(client, repository):
    client.put("/calendar/google", json={"client_id": "g-client", "client_secret": "s3cret"}, headers=OWNER)

    response = client.get("/calendar/google/connect?back=https://evil.test", headers=OWNER, follow_redirects=False)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_events_are_cached_for_a_few_minutes(repository, fake):
    connect_both(repository)
    service = CalendarService(repository, SECRET, httpx2.MockTransport(fake), Cached())

    asyncio.run(service.events(NOW))
    asked = len(fake.requests)
    asyncio.run(service.events(NOW))

    assert len(fake.requests) == asked


def event(title, start, minutes=60, all_day=False):
    return Event(id=title, title=title, start=start, end=start + timedelta(minutes=minutes), all_day=all_day, source="Google")


def test_calendar_lines_in_the_owners_time():
    text = calendar_lines([event("Database class", NOW + timedelta(minutes=5))], NOW, KL, [])

    assert "- Wed 14 Oct 09:05: Database class" in text


def test_first_message_today_asks_for_a_summary_or_says_free():
    assert "summary of today's events" in first_today_line([event("Gym", NOW + timedelta(hours=2))], NOW, KL)
    assert "free today" in first_today_line([event("Later", NOW + timedelta(days=2))], NOW, KL)


def test_due_soon_is_timed_events_in_the_next_minutes():
    soon = event("Class", NOW + timedelta(minutes=8))
    later = event("Later", NOW + timedelta(minutes=30))
    all_day = event("Holiday", NOW + timedelta(minutes=5), all_day=True)

    assert due_soon([soon, later, all_day], NOW, 10) == [soon]


def test_google_sign_in_link_asks_offline_read_and_event_access_with_pkce():
    url = Google().auth_url("cid", "http://localhost:3000/api/calendar/google/callback", "st", "chal")
    query = parse_qs(urlsplit(url).query)

    # Read every calendar, change only events (not calendars or sharing).
    assert query["scope"] == [
        "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events"
    ]
    assert query["access_type"] == ["offline"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == ["st"]


def test_microsoft_sign_in_link_asks_calendar_read_write():
    query = parse_qs(urlsplit(Microsoft().auth_url("cid", "http://x/cb", "st", "chal")).query)

    assert query["scope"] == ["offline_access User.Read Calendars.ReadWrite"]


# --- routes ------------------------------------------------------------------


@pytest.fixture
def client(repository, fake):
    engine = repository.engine
    sign_ins = SignIns()
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token="test-owner-token",
        database_url="sqlite+pysqlite:///:memory:",
        secret_key=SECRET,
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_calendar_repository] = lambda: repository
    app.dependency_overrides[get_calendar_service] = lambda: CalendarService(
        repository, SECRET, httpx2.MockTransport(fake), Cached(),
    )
    app.dependency_overrides[get_sign_ins] = lambda: sign_ins
    app.dependency_overrides[get_email_repository] = lambda: EmailRepository(engine)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_save_client_keeps_the_secret_hidden(client, repository):
    response = client.put("/calendar/google", json={"client_id": "g-client", "client_secret": "s3cret"}, headers=OWNER)

    assert response.status_code == status.HTTP_200_OK
    listed = client.get("/calendar", headers=OWNER | {"x-forwarded-host": "localhost:3000"}).json()
    google = next(item for item in listed if item["provider"] == "google")
    assert google["configured"] is True and google["connected"] is False
    assert google["redirect_uri"] == "http://localhost:3000/api/calendar/google/callback"
    assert "s3cret" not in str(listed)
    assert decrypt_text(repository.get("google").client_secret_encrypted, SECRET) == "s3cret"


def test_full_sign_in_round_trip(client, repository, fake):
    client.put("/calendar/google", json={"client_id": "g-client", "client_secret": "s3cret"}, headers=OWNER)

    start = client.get("/calendar/google/connect", headers=OWNER, follow_redirects=False)
    assert start.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    query = parse_qs(urlsplit(start.headers["location"]).query)

    back = client.get(
        f"/calendar/google/callback?state={query['state'][0]}&code=one-time-code",
        headers=OWNER, follow_redirects=False,
    )

    assert back.headers["location"] == "/settings/calendar?connected=google"
    account = repository.get("google")
    assert decrypt_text(account.refresh_token_encrypted, SECRET) == "g-refresh"
    assert account.account_email == "me@gmail.com"
    # PKCE: the token request carried the secret verifier that matches the challenge.
    token_request = next(r for r in fake.requests if "oauth2.googleapis.com/token" in str(r.url))
    assert b"code_verifier=" in token_request.content


def test_a_callback_this_venus_didnt_start_is_refused(client, repository):
    client.put("/calendar/google", json={"client_id": "g-client", "client_secret": "s3cret"}, headers=OWNER)

    back = client.get("/calendar/google/callback?state=forged&code=x", headers=OWNER, follow_redirects=False)

    assert "error=" in back.headers["location"]
    assert repository.get("google").refresh_token_encrypted is None


def test_upcoming_is_open_to_the_pc_and_events_need_the_owner(client, repository):
    connect_both(repository)

    assert client.get("/calendar/upcoming", headers=NODE).status_code == status.HTTP_200_OK
    assert client.get("/calendar/events", headers=NODE).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/calendar/events").status_code == status.HTTP_401_UNAUTHORIZED


def test_disconnect_forgets_everything(client, repository):
    connect_both(repository)

    assert client.delete("/calendar/google", headers=OWNER).status_code == status.HTTP_204_NO_CONTENT
    assert repository.get("google") is None


class FakeCalendar:
    def __init__(self, events):
        self.found = events

    def connected(self):
        return True

    async def events(self, now=None):
        return self.found, []


class FakeTime:
    def get_time(self):
        return type("Saved", (), {"time_zone": "Asia/Kuala_Lumpur", "country": ""})()


class FakeConversations:
    def __init__(self, today):
        self.today = today

    def user_messages_since(self, moment):
        return self.today


def test_luna_gets_the_week_and_a_morning_summary_only_on_the_first_message():
    from features.nodes.router import calendar_context

    soon = event("Database class", datetime.now(timezone.utc) + timedelta(hours=1))
    first = asyncio.run(calendar_context(FakeCalendar([soon]), FakeTime(), FakeConversations(1)))
    later = asyncio.run(calendar_context(FakeCalendar([soon]), FakeTime(), FakeConversations(3)))

    assert "Database class" in first and "first message today" in first
    assert "Database class" in later and "first message today" not in later


def test_user_messages_since_counts_every_chat():
    from features.conversations.repository import ConversationRepository

    engine = make_test_engine()
    conversations = ConversationRepository(engine)
    one = conversations.create("hi")
    conversations.add_message(one, "user", "hi")
    conversations.add_message(one, "assistant", "hey")
    two = conversations.create("yo")
    conversations.add_message(two, "user", "yo")

    assert conversations.user_messages_since(datetime.now(timezone.utc) - timedelta(minutes=1)) == 2
    assert conversations.user_messages_since(datetime.now(timezone.utc) + timedelta(minutes=1)) == 0
    engine.dispose()


@pytest.mark.parametrize(
    ("code", "says"),
    [
        ("access_denied", "publish it (or add yourself as a test user)"),
        ("invalid_client", "client ID or secret"),
        ("admin_consent_required", "admin has to approve"),
        ("something_new", "(something_new)"),
    ],
)
def test_sign_in_errors_say_what_to_do(code, says):
    from features.calendar.providers import sign_in_problem

    assert says in sign_in_problem("Google", code)
