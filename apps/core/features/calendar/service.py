import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx2
from cryptography.fernet import InvalidToken

from features.calendar.ics import fetch_ics, ics_events
from features.calendar.models.venus_event import VenusEvent
from features.calendar.providers import PROVIDERS, STATE_LIFETIME, CalendarError, Event, EventDraft, Provider
from features.calendar.repository import CalendarRepository
from features.settings.secrets import decrypt_text, encrypt_text

logger = logging.getLogger(__name__)

CACHE_SECONDS = 300
DAYS_AHEAD = 7
# Luna's instructions get at most this many events, so a busy week stays cheap.
MAX_EVENTS = 25
SIGNED_OUT = "{label} signed Venus out. Go to Settings, Calendar and press Reconnect."


@dataclass
class PendingSignIn:
    provider: str
    verifier: str
    redirect_uri: str
    expires: float
    # Started from Settings, Email: also ask for mail, and the name to send as.
    mail: bool = False
    name: str = ""


class SignIns:
    """Sign-ins started but not finished, by their random state.

    The state proves the browser coming back is the one that started it
    (CSRF), and the verifier is PKCE's secret. Kept in memory: a restart in
    the middle of signing in just means clicking Connect again.
    """

    def __init__(self) -> None:
        self._pending: dict[str, PendingSignIn] = {}

    def start(self, provider: str, verifier: str, redirect_uri: str, mail: bool = False, name: str = "") -> str:
        now = time.monotonic()
        self._pending = {key: value for key, value in self._pending.items() if value.expires > now}
        state = secrets.token_urlsafe(24)
        self._pending[state] = PendingSignIn(
            provider, verifier, redirect_uri, now + STATE_LIFETIME.total_seconds(), mail, name,
        )
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
        """The next week's events from every calendar, sorted, plus what failed (cached 5 minutes)."""
        if time.monotonic() - self.cache.at < CACHE_SECONDS and self.cache.at:
            return self.cache.events, self.cache.errors
        now = now or datetime.now(timezone.utc)
        # From the start of today (UTC) so today's earlier events count too.
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        events, errors = await self.between(start, now + timedelta(days=DAYS_AHEAD))
        self.cache.at, self.cache.events, self.cache.errors = time.monotonic(), events, errors
        return events, errors

    async def access_token(self, provider_name: str) -> str:
        account = self.repository.get(provider_name)
        if account is None or not account.refresh_token_encrypted:
            raise CalendarError(f"{PROVIDERS[provider_name].label} isn't connected. Connect it in Settings, Calendar.")
        try:
            refresh_token = decrypt_text(account.refresh_token_encrypted, self.secret_key)
            client_secret = decrypt_text(account.client_secret_encrypted, self.secret_key)
        except InvalidToken as exc:
            label = PROVIDERS[provider_name].label
            raise CalendarError(f"{label}: the saved sign-in can't be read. Connect it again in Settings, Calendar.") from exc
        label = PROVIDERS[provider_name].label
        if account.signed_out_at is not None:
            raise CalendarError(SIGNED_OUT.format(label=label), "invalid_grant")
        try:
            tokens = await self.provider(provider_name).refresh(
                refresh_token, account.client_id, client_secret, mail=bool(account.mail),
            )
        except CalendarError as exc:
            if exc.code != "invalid_grant":
                raise
            # Remembered, so Settings can say so and Venus stops asking.
            self.repository.mark_signed_out(provider_name, datetime.now(timezone.utc))
            raise CalendarError(SIGNED_OUT.format(label=label), exc.code) from exc
        if tokens.refresh_token:
            self.repository.save_refresh_token(provider_name, encrypt_text(tokens.refresh_token, self.secret_key))
        return tokens.access_token

    async def between(self, start: datetime, end: datetime) -> tuple[list[Event], list[str]]:
        """Every calendar's events from start to end (no cache: the Calendar page's month or week)."""
        events: list[Event] = [venus_event(event) for event in self.repository.venus_events(start, end)]
        errors: list[str] = []
        for account in self.repository.list_all():
            if not account.refresh_token_encrypted:
                continue
            provider = self.provider(account.provider)
            try:
                events.extend(await provider.events(await self.access_token(account.provider), start, end))
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
            except InvalidToken:
                errors.append(f"{calendar.name}: the saved link can't be read. Remove it and add it again.")
            except (CalendarError, httpx2.HTTPError, ValueError) as exc:
                logger.warning("Calendar %s failed: %s", calendar.name, exc)
                errors.append(f"{calendar.name}: {exc}" if isinstance(exc, CalendarError) else f"{calendar.name} couldn't be read")
        events.sort(key=lambda event: event.start)
        return events, errors

    def writable(self) -> list[dict]:
        """Calendars a new event can go to: Venus's own, then connected Google/Outlook."""
        options = [{"id": "venus", "label": "Venus"}]
        for account in self.repository.list_all():
            if account.refresh_token_encrypted:
                label = PROVIDERS[account.provider].label
                options.append({"id": account.provider, "label": f"{label} ({account.account_email})" if account.account_email else label})
        return options

    async def create(self, calendar: str, draft: EventDraft, now: datetime | None = None) -> str:
        """Adds an event; its id (venus:..., google:..., microsoft:...)."""
        if calendar == "venus":
            event = self.repository.add_venus_event(VenusEvent(
                draft.title, draft.start, draft.end, now or datetime.now(timezone.utc),
                all_day=draft.all_day, location=draft.location, notes=draft.notes,
            ))
            new_id = f"venus:{event.id}"
        elif calendar in PROVIDERS:
            new_id = f"{calendar}:{await self.provider(calendar).create(await self.access_token(calendar), draft)}"
        else:
            raise CalendarError("Pick Venus, Google or Outlook.")
        self.forget()
        return new_id

    async def update(self, event_id: str, draft: EventDraft) -> None:
        source, _, inner = event_id.partition(":")
        if source == "venus":
            found = self.repository.update_venus_event(
                venus_id(inner), title=draft.title, start=draft.start, end=draft.end,
                all_day=draft.all_day, location=draft.location, notes=draft.notes,
            )
            if not found:
                raise CalendarError("That event isn't on your Venus calendar anymore.")
        elif source in PROVIDERS:
            await self.provider(source).update(await self.access_token(source), inner, draft)
        else:
            raise CalendarError("Timetables (.ics) can't be changed from Venus.")
        self.forget()

    async def delete(self, event_id: str) -> None:
        source, _, inner = event_id.partition(":")
        if source == "venus":
            if not self.repository.delete_venus_event(venus_id(inner)):
                raise CalendarError("That event isn't on your Venus calendar anymore.")
        elif source in PROVIDERS:
            await self.provider(source).delete(await self.access_token(source), inner)
        else:
            raise CalendarError("Timetables (.ics) can't be changed from Venus.")
        self.forget()

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


def venus_id(text: str) -> UUID:
    try:
        return UUID(text)
    except ValueError as exc:
        raise CalendarError("That isn't a Venus event id.") from exc


def venus_event(event: VenusEvent) -> Event:
    return Event(
        id=f"venus:{event.id}",
        title=event.title,
        start=event.start if event.start.tzinfo else event.start.replace(tzinfo=timezone.utc),
        end=event.end if event.end.tzinfo else event.end.replace(tzinfo=timezone.utc),
        all_day=event.all_day,
        source="Venus",
        location=event.location,
        notes=event.notes,
        editable=True,
    )
