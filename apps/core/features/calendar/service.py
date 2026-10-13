import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx2

from features.calendar.ics import fetch_ics, ics_events
from features.calendar.providers import PROVIDERS, STATE_LIFETIME, CalendarError, Event, Provider
from features.calendar.repository import CalendarRepository
from features.settings.secrets import decrypt_text, encrypt_text

logger = logging.getLogger(__name__)

CACHE_SECONDS = 300
DAYS_AHEAD = 7
# Luna's instructions get at most this many events, so a busy week stays cheap.
MAX_EVENTS = 25


@dataclass
class PendingSignIn:
    provider: str
    verifier: str
    redirect_uri: str
    expires: float


class SignIns:
    """Sign-ins started but not finished, by their random state.

    The state proves the browser coming back is the one that started it
    (CSRF), and the verifier is PKCE's secret. Kept in memory: a restart in
    the middle of signing in just means clicking Connect again.
    """

    def __init__(self) -> None:
        self._pending: dict[str, PendingSignIn] = {}

    def start(self, provider: str, verifier: str, redirect_uri: str) -> str:
        now = time.monotonic()
        self._pending = {key: value for key, value in self._pending.items() if value.expires > now}
        state = secrets.token_urlsafe(24)
        self._pending[state] = PendingSignIn(provider, verifier, redirect_uri, now + STATE_LIFETIME.total_seconds())
        return state

    def finish(self, state: str, provider: str) -> PendingSignIn | None:
        pending = self._pending.pop(state, None)
        if pending is None or pending.provider != provider or pending.expires < time.monotonic():
            return None
        return pending


@dataclass
class Cached:
    at: float = 0.0
    events: list[Event] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class CalendarService:
    def __init__(
        self,
        repository: CalendarRepository,
        secret_key: str,
        transport: httpx2.AsyncBaseTransport | None = None,
        cache: Cached | None = None,
        zone: ZoneInfo | None = None,
    ) -> None:
        self.repository = repository
        self.secret_key = secret_key
        self.transport = transport
        self.cache = cache if cache is not None else Cached()
        # .ics times without a zone (common in timetables) are the owner's time.
        self.zone = zone or ZoneInfo("UTC")

    def provider(self, name: str) -> Provider:
        return PROVIDERS[name](self.transport)

    def connected(self) -> bool:
        return bool(self.repository.list_ics()) or any(
            account.refresh_token_encrypted for account in self.repository.list_all()
        )

    async def events(self, now: datetime | None = None) -> tuple[list[Event], list[str]]:
        """The next week's events from every connected calendar, sorted, plus what failed."""
        if time.monotonic() - self.cache.at < CACHE_SECONDS and self.cache.at:
            return self.cache.events, self.cache.errors
        now = now or datetime.now(timezone.utc)
        # From the start of today (UTC) so today's earlier events count too.
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        end = now + timedelta(days=DAYS_AHEAD)
        events: list[Event] = []
        errors: list[str] = []
        for account in self.repository.list_all():
            if not account.refresh_token_encrypted:
                continue
            provider = self.provider(account.provider)
            try:
                tokens = await provider.refresh(
                    decrypt_text(account.refresh_token_encrypted, self.secret_key),
                    account.client_id,
                    decrypt_text(account.client_secret_encrypted, self.secret_key),
                )
                if tokens.refresh_token:
                    self.repository.save_refresh_token(account.provider, encrypt_text(tokens.refresh_token, self.secret_key))
                events.extend(await provider.events(tokens.access_token, start, end))
            except (CalendarError, httpx2.HTTPError, KeyError, ValueError) as exc:
                logger.warning("Calendar %s failed: %s", account.provider, exc)
                errors.append(str(exc) if isinstance(exc, CalendarError) else f"{provider.label} calendar didn't answer")
        for calendar in self.repository.list_ics():
            try:
                if calendar.url_encrypted:
                    text = await fetch_ics(decrypt_text(calendar.url_encrypted, self.secret_key), self.transport)
                else:
                    text = calendar.content or ""
                events.extend(ics_events(text, start, end, calendar.name, self.zone))
            except (CalendarError, httpx2.HTTPError, ValueError) as exc:
                logger.warning("Calendar %s failed: %s", calendar.name, exc)
                errors.append(f"{calendar.name}: {exc}" if isinstance(exc, CalendarError) else f"{calendar.name} couldn't be read")
        events.sort(key=lambda event: event.start)
        self.cache.at, self.cache.events, self.cache.errors = time.monotonic(), events, errors
        return events, errors

    def forget(self) -> None:
        self.cache.at = 0.0


def when(event: Event, zone: ZoneInfo) -> str:
    if event.all_day:
        return event.start.strftime("%a %d %b") + " (all day)"
    local = event.start.astimezone(zone)
    return local.strftime("%a %d %b %H:%M")


def calendar_lines(events: list[Event], now: datetime, zone: ZoneInfo, errors: list[str]) -> str:
    """The owner's coming week for Luna's instructions, short to keep every message cheap."""
    upcoming = [event for event in events if event.end > now][:MAX_EVENTS]
    parts = []
    if upcoming:
        rows = [
            f"- {when(event, zone)}: {event.title}" + (f" @ {event.location}" if event.location else "")
            for event in upcoming
        ]
        parts.append("The owner's calendar for the next 7 days (their time):\n" + "\n".join(rows))
    else:
        parts.append("The owner's calendar has nothing in the next 7 days.")
    if errors:
        parts.append("Calendar problems (say so if they ask about their schedule): " + "; ".join(errors))
    return "\n".join(parts)


def first_today_line(events: list[Event], now: datetime, zone: ZoneInfo) -> str:
    today = now.astimezone(zone).date()
    todays = [e for e in events if (e.start.date() if e.all_day else e.start.astimezone(zone).date()) == today]
    if not todays:
        return "This is the owner's first message today. Start with a short good morning and say their calendar is free today."
    return (
        "This is the owner's first message today. Start with a one or two sentence summary of today's "
        "events from the calendar, then answer them."
    )


def due_soon(events: list[Event], now: datetime, minutes: int) -> list[Event]:
    """Timed events starting within the next few minutes (for the PC's reminder pop-ups)."""
    until = now + timedelta(minutes=minutes)
    return [event for event in events if not event.all_day and now <= event.start <= until]
