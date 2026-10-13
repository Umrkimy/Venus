"""Calendars from .ics links and files (uni timetables)."""

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx2
import pytest
from cryptography.fernet import Fernet
from fastapi import status
from fastapi.testclient import TestClient

from config import CoreSettings, get_settings
from features.auth.dependencies import get_auth_repository
from features.auth.repository import AuthRepository
from features.calendar.dependencies import get_calendar_repository, get_calendar_service
from features.calendar.ics import ics_events, link_to_fetch
from features.calendar.providers import CalendarError
from features.calendar.repository import CalendarRepository
from features.calendar.service import Cached, CalendarService
from features.settings.secrets import decrypt_text
from main import app
from tests.database import make_test_engine

SECRET = Fernet.generate_key().decode()
OWNER = {"Authorization": "Bearer test-owner-token"}
KL = ZoneInfo("Asia/Kuala_Lumpur")
LINK = "webcal://portal.uni.example/timetable.ics?key=private-key-123"

# Monday 2026-10-12 onwards: a weekly lecture (with its own zone), a lab with
# no zone (floating: the owner's time), an all-day exam and a cancelled class.
TIMETABLE = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Uni//Timetable//EN
BEGIN:VEVENT
UID:lecture-1
SUMMARY:Data Structures lecture
LOCATION:Hall B
DTSTART;TZID=Asia/Kuala_Lumpur:20261012T090000
DTEND;TZID=Asia/Kuala_Lumpur:20261012T110000
RRULE:FREQ=WEEKLY;COUNT=14
END:VEVENT
BEGIN:VEVENT
UID:lab-1
SUMMARY:Networks lab
DTSTART:20261014T140000
DTEND:20261014T160000
END:VEVENT
BEGIN:VEVENT
UID:exam-1
SUMMARY:Midterm week
DTSTART;VALUE=DATE:20261016
DTEND;VALUE=DATE:20261017
END:VEVENT
BEGIN:VEVENT
UID:cancelled-1
SUMMARY:Cancelled tutorial
STATUS:CANCELLED
DTSTART:20261013T100000Z
DTEND:20261013T110000Z
END:VEVENT
END:VCALENDAR
"""

client = TestClient(app)
fetched: list[str] = []


def fake_portal(request: httpx2.Request) -> httpx2.Response:
    fetched.append(str(request.url))
    if request.url.host == "portal.uni.example":
        return httpx2.Response(200, text=TIMETABLE)
    return httpx2.Response(404)


@pytest.fixture(autouse=True)
def repository():
    engine = make_test_engine()
    repository = CalendarRepository(engine)
    fetched.clear()
    app.dependency_overrides[get_settings] = lambda: CoreSettings(
        dev_node_token="test-node-token",
        dev_owner_token="test-owner-token",
        database_url="sqlite+pysqlite:///:memory:",
        secret_key=SECRET,
    )
    app.dependency_overrides[get_auth_repository] = lambda: AuthRepository(engine)
    app.dependency_overrides[get_calendar_repository] = lambda: repository
    app.dependency_overrides[get_calendar_service] = lambda: CalendarService(
        repository, SECRET, httpx2.MockTransport(fake_portal), Cached(), zone=KL,
    )
    yield repository
    app.dependency_overrides.clear()
    engine.dispose()


def week(start=datetime(2026, 10, 12, tzinfo=timezone.utc)):
    return ics_events(TIMETABLE, start - timedelta(hours=12), start + timedelta(days=7), "Uni", KL)


def test_weekly_class_floating_lab_all_day_exam_and_no_cancelled():
    events = {event.title: event for event in week()}

    assert set(events) == {"Data Structures lecture", "Networks lab", "Midterm week"}
    lecture = events["Data Structures lecture"]
    assert lecture.start == datetime(2026, 10, 12, 1, 0, tzinfo=timezone.utc)  # 9:00 in KL
    assert (lecture.location, lecture.source, lecture.all_day) == ("Hall B", "Uni", False)
    # No zone in the file: it's the owner's own 14:00.
    assert events["Networks lab"].start == datetime(2026, 10, 14, 6, 0, tzinfo=timezone.utc)
    assert events["Midterm week"].all_day is True


def test_repeating_class_shows_every_week():
    weeks = ics_events(
        TIMETABLE, datetime(2026, 10, 11, tzinfo=timezone.utc), datetime(2026, 11, 2, tzinfo=timezone.utc), "Uni", KL,
    )

    lectures = [event.start for event in weeks if event.title == "Data Structures lecture"]
    assert len(lectures) == 3
    assert len({event.id for event in weeks}) == len(weeks)  # each one has its own id


@pytest.mark.parametrize(
    ("link", "fetched_as"),
    [
        ("webcal://portal.uni.example/t.ics", "https://portal.uni.example/t.ics"),
        ("https://portal.uni.example/t.ics", "https://portal.uni.example/t.ics"),
    ],
)
def test_webcal_is_https(link, fetched_as):
    assert link_to_fetch(link) == fetched_as


def test_other_link_kinds_are_refused():
    with pytest.raises(CalendarError):
        link_to_fetch("file:///etc/passwd")


def test_upload_a_file_says_how_many_events_are_coming(repository: CalendarRepository):
    response = client.post("/calendar/ics", json={"name": " Uni timetable ", "content": TIMETABLE}, headers=OWNER)

    assert response.status_code == status.HTTP_201_CREATED, response.text
    assert response.json()["name"] == "Uni timetable"
    assert response.json()["kind"] == "file"
    assert isinstance(response.json()["events_next_4_weeks"], int)
    assert repository.list_ics()[0].content == TIMETABLE
    assert client.get("/calendar/ics", headers=OWNER).json() == [
        {"id": response.json()["id"], "name": "Uni timetable", "kind": "file"},
    ]


def test_a_link_is_checked_saved_encrypted_and_never_shown(repository: CalendarRepository):
    response = client.post("/calendar/ics", json={"name": "Exams", "url": LINK}, headers=OWNER)

    assert response.status_code == status.HTTP_201_CREATED, response.text
    assert fetched == ["https://portal.uni.example/timetable.ics?key=private-key-123"]
    saved = repository.list_ics()[0]
    assert saved.content is None
    assert decrypt_text(saved.url_encrypted, SECRET) == LINK
    assert "private-key" not in client.get("/calendar/ics", headers=OWNER).text


@pytest.mark.parametrize(
    ("body", "says"),
    [
        ({"name": "x", "content": "hello"}, "isn't a calendar"),
        ({"name": "x", "url": "https://elsewhere.example/a.ics"}, "answered 404"),
        ({"name": "x", "url": "ftp://portal.uni.example/a.ics"}, "must start with"),
        ({"name": "x", "url": LINK, "content": TIMETABLE}, "not both"),
        ({"name": "x"}, "not both"),
        ({"name": "   ", "content": TIMETABLE}, ""),
    ],
)
def test_bad_calendars_are_refused(body, says):
    response = client.post("/calendar/ics", json=body, headers=OWNER)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert says in response.text


def test_same_name_twice_is_409_and_remove_works(repository: CalendarRepository):
    first = client.post("/calendar/ics", json={"name": "Uni", "content": TIMETABLE}, headers=OWNER).json()

    again = client.post("/calendar/ics", json={"name": "Uni", "content": TIMETABLE}, headers=OWNER)
    removed = client.delete(f"/calendar/ics/{first['id']}", headers=OWNER)

    assert again.status_code == status.HTTP_409_CONFLICT
    assert removed.status_code == status.HTTP_204_NO_CONTENT
    assert repository.list_ics() == []
    assert client.delete(f"/calendar/ics/{first['id']}", headers=OWNER).status_code == status.HTTP_404_NOT_FOUND


def test_service_merges_ics_and_reports_a_broken_link(repository: CalendarRepository):
    now = datetime(2026, 10, 13, 0, 0, tzinfo=timezone.utc)
    repository.add_ics("Uni", now, content=TIMETABLE)
    from features.settings.secrets import encrypt_text

    repository.add_ics("Club", now, url_encrypted=encrypt_text("https://gone.example/c.ics", SECRET))
    service = CalendarService(repository, SECRET, httpx2.MockTransport(fake_portal), Cached(), zone=KL)

    assert service.connected() is True
    events, errors = asyncio.run(service.events(now))

    assert "Networks lab" in [event.title for event in events]
    assert events == sorted(events, key=lambda event: event.start)
    assert errors == ["Club: The calendar link answered 404."]


def test_ics_needs_the_owner():
    assert client.get("/calendar/ics").status_code == status.HTTP_401_UNAUTHORIZED
