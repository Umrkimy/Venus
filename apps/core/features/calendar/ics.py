"""Calendars from .ics links and files (a uni timetable, exam dates...).

.ics is the standard calendar format every calendar app can export. A
timetable is mostly repeating events ("every Monday 9:00 until December"),
so recurring_ical_events turns those rules into the actual dates.
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import httpx2
import icalendar
import recurring_ical_events

from features.calendar.providers import CalendarError, Event

# A whole semester's timetable is well under this.
MAX_BYTES = 2_000_000


def check_ics(text: str) -> str:
    if len(text.encode()) > MAX_BYTES:
        raise CalendarError("That calendar file is too big (over 2 MB).")
    if "BEGIN:VCALENDAR" not in text[:2000].upper():
        raise CalendarError("That isn't a calendar (.ics) file.")
    try:
        icalendar.Calendar.from_ical(text)
    except ValueError as exc:
        raise CalendarError("That calendar file couldn't be read.") from exc
    return text


def link_to_fetch(url: str) -> str:
    """webcal:// is just https:// for calendars."""
    url = url.strip()
    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    if not url.lower().startswith(("https://", "http://")):
        raise CalendarError("The link must start with https://, http:// or webcal://")
    return url


async def fetch_ics(url: str, transport: httpx2.AsyncBaseTransport | None = None) -> str:
    try:
        async with httpx2.AsyncClient(transport=transport, timeout=15, follow_redirects=True) as client:
            response = await client.get(link_to_fetch(url))
    except httpx2.HTTPError as exc:
        raise CalendarError("Couldn't download that calendar link.") from exc
    if response.status_code != 200:
        raise CalendarError(f"The calendar link answered {response.status_code}.")
    if len(response.content) > MAX_BYTES:
        raise CalendarError("That calendar is too big (over 2 MB).")
    return check_ics(response.text)


def as_aware(value: date | datetime, zone: ZoneInfo) -> tuple[datetime, bool]:
    """(start or end, all day?). Times without a zone are the owner's own time."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=zone)
        return value.astimezone(timezone.utc), False
    return datetime.combine(value, time(), tzinfo=timezone.utc), True


def ics_events(text: str, start: datetime, end: datetime, source: str, zone: ZoneInfo) -> list[Event]:
    calendar = icalendar.Calendar.from_ical(text)
    events = []
    for component in recurring_ical_events.of(calendar).between(start, end):
        if str(component.get("STATUS", "")).upper() == "CANCELLED":
            continue
        begins = component.get("DTSTART")
        if begins is None:
            continue
        event_start, all_day = as_aware(begins.dt, zone)
        finishes = component.get("DTEND")
        event_end = as_aware(finishes.dt, zone)[0] if finishes is not None else event_start
        if event_end < event_start:
            event_end = event_start
        events.append(Event(
            id=f"{component.get('UID', '')}@{event_start.isoformat()}",
            title=str(component.get("SUMMARY", "")).strip() or "(no title)",
            start=event_start,
            end=event_end,
            all_day=all_day,
            source=source,
            location=str(component.get("LOCATION", "")).strip(),
        ))
    return events
