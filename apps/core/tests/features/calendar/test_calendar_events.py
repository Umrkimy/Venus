"""The Calendar page: events for a range, and adding, changing and deleting them."""

import json
from datetime import datetime, timedelta, timezone

import httpx2
import pytest
from cryptography.fernet import Fernet
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.calendar.dependencies import get_calendar_repository, get_calendar_service
from features.calendar.repository import CalendarRepository
from features.calendar.service import Cached, CalendarService
from features.settings.secrets import encrypt_text
from main import app
from tests.database import make_test_engine

SECRET = Fernet.generate_key().decode()
OWNER = {"Authorization": "Bearer test-owner-token"}
NOW = datetime(2026, 10, 14, 1, 0, tzinfo=timezone.utc)
MONTH = {"start": "2026-10-01T00:00:00Z", "end": "2026-11-01T00:00:00Z"}
GYM = {"title": "Gym", "start": "2026-10-15T10:00:00Z", "end": "2026-10-15T11:00:00Z", "location": "Uni gym"}
TIMETABLE = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:lecture
SUMMARY:Lecture
DTSTART:20261016T010000Z
DTEND:20261016T030000Z
END:VEVENT
END:VCALENDAR
"""

client = TestClient(app)


class FakeProviders:
    """Google and Microsoft: tokens, one event each, and whatever Venus writes."""

    def __init__(self) -> None:
        self.writes: list[tuple[str, str, dict | None]] = []
        self.refuse = False

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        url = str(request.url)
        if "oauth2.googleapis.com/token" in url:
            return httpx2.Response(200, json={"access_token": "g-access"})
        if "login.microsoftonline.com" in url:
            return httpx2.Response(200, json={"access_token": "m-access"})
        if request.method != "GET":
            body = json.loads(request.content) if request.content else None
            self.writes.append((request.method, url, body))
            if self.refuse:
                return httpx2.Response(403, json={"error": "insufficientPermissions"})
            if request.method == "DELETE":
                return httpx2.Response(204)
            return httpx2.Response(200, json={"id": "new-id"})
        if "calendarList" in url:
            return httpx2.Response(200, json={"items": [
                {"id": "me@gmail.com", "primary": True, "accessRole": "owner"},
                {"id": "holidays@group", "selected": True, "accessRole": "reader"},
            ]})
        url = url.replace("%40", "@")
        if "/calendars/me@gmail.com/events" in url:
            return httpx2.Response(200, json={"items": [{"id": "g1", "summary": "Dinner", "description": "with Aina",
                "start": {"dateTime": "2026-10-17T11:00:00Z"}, "end": {"dateTime": "2026-10-17T12:00:00Z"}}]})
        if "/calendars/holidays@group/events" in url:
            return httpx2.Response(200, json={"items": [{"id": "h1", "summary": "Deepavali",
                "start": {"date": "2026-11-08"}, "end": {"date": "2026-11-09"}}]})
        if "calendarView" in url:
            return httpx2.Response(200, json={"value": []})
        return httpx2.Response(404)


@pytest.fixture
def fake():
    return FakeProviders()


@pytest.fixture(autouse=True)
def repository(fake):
    engine = make_test_engine()
    repository = CalendarRepository(engine)
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
    yield repository
    app.dependency_overrides.clear()
    engine.dispose()


def connect(repository: CalendarRepository, name: str, email: str | None = None) -> None:
    repository.save_client(name, f"{name}-client", encrypt_text(f"{name}-secret", SECRET))
    repository.connect(name, encrypt_text(f"{name}-refresh", SECRET), email, NOW)


def month() -> dict:
    response = client.get("/calendar/events", params=MONTH, headers=OWNER)
    assert response.status_code == status.HTTP_200_OK, response.text
    return response.json()


def test_venus_event_add_change_delete():
    added = client.post("/calendar/events", json=GYM, headers=OWNER)

    assert added.status_code == status.HTTP_201_CREATED, added.text
    event_id = added.json()["id"]
    assert event_id.startswith("venus:")
    [event] = month()["events"]
    assert (event["title"], event["location"], event["source"], event["editable"]) == ("Gym", "Uni gym", "Venus", True)

    changed = client.patch(f"/calendar/events/{event_id}", json=GYM | {"title": "Gym (legs)", "start": "2026-10-15T12:00:00Z", "end": "2026-10-15T13:00:00Z"}, headers=OWNER)
    assert changed.status_code == status.HTTP_200_OK
    [event] = month()["events"]
    assert (event["title"], event["start"]) == ("Gym (legs)", "2026-10-15T12:00:00+00:00")

    assert client.delete(f"/calendar/events/{event_id}", headers=OWNER).status_code == status.HTTP_204_NO_CONTENT
    assert month()["events"] == []
    assert client.delete(f"/calendar/events/{event_id}", headers=OWNER).status_code == status.HTTP_409_CONFLICT


def test_all_day_event_and_range_only_returns_overlaps():
    client.post("/calendar/events", json={"title": "Exam week", "all_day": True,
        "start": "2026-10-19T00:00:00Z", "end": "2026-10-24T00:00:00Z"}, headers=OWNER)
    client.post("/calendar/events", json=GYM | {"start": "2026-12-01T10:00:00Z", "end": "2026-12-01T11:00:00Z"}, headers=OWNER)

    events = month()["events"]

    assert [(e["title"], e["all_day"]) for e in events] == [("Exam week", True)]


def test_page_range_mixes_every_calendar_and_marks_what_can_change(repository: CalendarRepository):
    connect(repository, "google")
    repository.add_ics("Uni", NOW, content=TIMETABLE)
    client.post("/calendar/events", json=GYM, headers=OWNER)

    events = client.get("/calendar/events", params={"start": "2026-10-01T00:00:00Z", "end": "2026-12-01T00:00:00Z"}, headers=OWNER).json()["events"]

    editable = {e["title"]: (e["source"], e["editable"]) for e in events}
    assert editable == {
        "Gym": ("Venus", True),
        "Lecture": ("Uni", False),
        "Dinner": ("Google", True),
        "Deepavali": ("Google", False),  # A calendar you can only read.
    }
    dinner = next(e for e in events if e["title"] == "Dinner")
    assert dinner["id"] == "google:me@gmail.com|g1"
    assert dinner["notes"] == "with Aina"


def test_google_add_change_delete(repository: CalendarRepository, fake: FakeProviders):
    connect(repository, "google")

    added = client.post("/calendar/events", json=GYM | {"calendar": "google", "notes": "bring towel"}, headers=OWNER)
    changed = client.patch("/calendar/events/google:me@gmail.com|g1", json=GYM, headers=OWNER)
    deleted = client.delete("/calendar/events/google:me@gmail.com|g1", headers=OWNER)

    assert added.json() == {"id": "google:primary|new-id"}
    assert changed.status_code == status.HTTP_200_OK
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    (post, post_url, body), (patch, patch_url, _), (delete, delete_url, _) = fake.writes
    assert (post, post_url) == ("POST", "https://www.googleapis.com/calendar/v3/calendars/primary/events")
    assert body == {"summary": "Gym", "location": "Uni gym", "description": "bring towel",
                    "start": {"dateTime": "2026-10-15T10:00:00Z"}, "end": {"dateTime": "2026-10-15T11:00:00Z"}}
    assert (patch, patch_url) == ("PATCH", "https://www.googleapis.com/calendar/v3/calendars/me%40gmail.com/events/g1")
    assert delete == "DELETE" and delete_url == patch_url


def test_google_all_day_uses_dates(repository: CalendarRepository, fake: FakeProviders):
    connect(repository, "google")

    client.post("/calendar/events", json={"title": "Trip", "all_day": True, "calendar": "google",
        "start": "2026-10-20T00:00:00Z", "end": "2026-10-22T00:00:00Z"}, headers=OWNER)

    body = fake.writes[0][2]
    assert (body["start"], body["end"]) == ({"date": "2026-10-20"}, {"date": "2026-10-22"})


def test_outlook_add_sends_graph_event(repository: CalendarRepository, fake: FakeProviders):
    connect(repository, "microsoft")

    added = client.post("/calendar/events", json=GYM | {"calendar": "microsoft"}, headers=OWNER)

    assert added.json() == {"id": "microsoft:new-id"}
    method, url, body = fake.writes[0]
    assert (method, url) == ("POST", "https://graph.microsoft.com/v1.0/me/events")
    assert body["subject"] == "Gym"
    assert body["start"] == {"dateTime": "2026-10-15T10:00:00", "timeZone": "UTC"}
    assert body["location"] == {"displayName": "Uni gym"}


def test_old_read_only_sign_in_says_reconnect(repository: CalendarRepository, fake: FakeProviders):
    connect(repository, "google")
    fake.refuse = True

    response = client.post("/calendar/events", json=GYM | {"calendar": "google"}, headers=OWNER)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "Reconnect it in Settings, Calendar" in response.json()["detail"]


@pytest.mark.parametrize(
    ("body", "why"),
    [
        (GYM | {"calendar": "google"}, "isn't connected"),  # Not connected.
        (GYM | {"calendar": "icloud"}, ""),  # Not a calendar Venus can write.
    ],
)
def test_adding_somewhere_venus_cant_write(body, why):
    response = client.post("/calendar/events", json=body, headers=OWNER)

    assert response.status_code in (status.HTTP_409_CONFLICT, status.HTTP_422_UNPROCESSABLE_CONTENT)
    assert why in response.text


def test_timetable_events_cant_be_changed():
    response = client.patch("/calendar/events/Uni:lecture@2026-10-16", json=GYM, headers=OWNER)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "can't be changed" in response.json()["detail"]


@pytest.mark.parametrize(
    "change",
    [
        {"title": "  "},
        {"end": "2026-10-15T09:00:00Z"},  # ends before it starts
        {"start": "2026-10-15T10:00:00"},  # no time zone
        {"end": "2028-01-01T00:00:00Z"},  # over a year
    ],
)
def test_bad_events_are_refused(change):
    assert client.post("/calendar/events", json=GYM | change, headers=OWNER).status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-10-01T00:00:00Z", "end": "2028-01-01T00:00:00Z"},  # too wide
        {"start": "2026-10-10T00:00:00Z", "end": "2026-10-01T00:00:00Z"},  # backwards
    ],
)
def test_bad_ranges_are_refused(params):
    assert client.get("/calendar/events", params=params, headers=OWNER).status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_writable_lists_venus_then_connected_accounts(repository: CalendarRepository):
    assert client.get("/calendar/writable", headers=OWNER).json() == [{"id": "venus", "label": "Venus"}]

    connect(repository, "google", "me@gmail.com")

    assert client.get("/calendar/writable", headers=OWNER).json() == [
        {"id": "venus", "label": "Venus"},
        {"id": "google", "label": "Google (me@gmail.com)"},
    ]


def test_venus_events_reach_lunas_week_and_reminders(repository: CalendarRepository):
    import asyncio

    service = CalendarService(repository, SECRET, None, Cached())
    asyncio.run(service.create("venus", __import__("features.calendar.providers", fromlist=["EventDraft"]).EventDraft(
        "Dentist", NOW + timedelta(hours=2), NOW + timedelta(hours=3)), now=NOW))

    events, errors = asyncio.run(service.events(NOW))

    assert [event.title for event in events] == ["Dentist"] and errors == []


def test_calendar_page_needs_the_owner():
    assert client.get("/calendar/events", params=MONTH).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.post("/calendar/events", json=GYM).status_code == status.HTTP_401_UNAUTHORIZED


def test_a_link_saved_with_another_secret_key_is_an_error_not_a_crash(repository: CalendarRepository):
    other_key = Fernet.generate_key().decode()
    repository.add_ics("Uni", NOW, url_encrypted=encrypt_text("https://portal.example/t.ics", other_key))
    client.post("/calendar/events", json=GYM, headers=OWNER)

    body = month()

    assert [e["title"] for e in body["events"]] == ["Gym"]
    assert body["errors"] == ["Uni: the saved link can't be read. Remove it and add it again."]


def test_google_calendar_ids_with_a_hash_are_encoded_and_one_bad_calendar_is_skipped(repository: CalendarRepository, fake: FakeProviders):
    import httpx2 as h

    seen = []
    original = fake.__call__

    def google(request: h.Request) -> h.Response:
        url = str(request.url)
        seen.append(url)
        if "calendarList" in url:
            return h.Response(200, json={"items": [
                {"id": "me@gmail.com", "primary": True, "accessRole": "owner"},
                {"id": "en.malaysia#holiday@group.v.calendar.google.com", "selected": True, "accessRole": "reader"},
                {"id": "gone@group.calendar.google.com", "selected": True, "accessRole": "reader"},
            ]})
        if "en.malaysia%23holiday@group" in url:
            return h.Response(200, json={"items": [{"id": "dv", "summary": "Deepavali",
                "start": {"date": "2026-10-20"}, "end": {"date": "2026-10-21"}}]})
        if "gone@group" in url:
            return h.Response(404)
        return original(request)

    app.dependency_overrides[get_calendar_service] = lambda: CalendarService(repository, SECRET, httpx2.MockTransport(google), Cached())
    connect(repository, "google")

    body = month()

    assert {e["title"] for e in body["events"]} == {"Dinner", "Deepavali"}
    assert body["errors"] == []
    assert any("en.malaysia%23holiday@group.v.calendar.google.com/events" in url for url in seen)
