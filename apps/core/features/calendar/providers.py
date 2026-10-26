"""Google Calendar and Microsoft (Outlook) calendars over OAuth, read-only.

Both use the same OAuth "authorization code + PKCE" flow: the browser goes
to Google or Microsoft, you say yes, they send the browser back with a
one-time code, and Core trades that code (plus the secret proof from PKCE)
for tokens. Only the refresh token is kept, encrypted.
"""

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import httpx2


class CalendarError(Exception):
    """Google or Microsoft said no; the message is safe to show."""

    def __init__(self, message: str, code: str = "") -> None:
        super().__init__(message)
        # The provider's own error code, e.g. invalid_grant (signed out).
        self.code = code


@dataclass(frozen=True)
class Event:
    id: str
    title: str
    start: datetime  # Timezone-aware; all-day events start at midnight UTC of that day.
    end: datetime
    all_day: bool
    source: str  # "Google", "Outlook", "Venus" or an .ics calendar's name
    location: str = ""
    notes: str = ""
    # Can Venus change it? Its own, and Google/Outlook ones you may edit; .ics never.
    editable: bool = False


@dataclass(frozen=True)
class EventDraft:
    """A new or changed event, as the Calendar page sends it."""

    title: str
    start: datetime
    end: datetime
    all_day: bool = False
    location: str = ""
    notes: str = ""


@dataclass(frozen=True)
class Tokens:
    access_token: str
    refresh_token: str | None
    email: str | None = None


def pkce_pair() -> tuple[str, str]:
    """A random secret (verifier) and its SHA-256 (challenge), for PKCE."""
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Provider:
    name: str
    label: str
    auth_endpoint: str
    token_endpoint: str
    scope: str

    def __init__(self, transport: httpx2.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    def client(self) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(transport=self._transport, timeout=15)

    # Extra permission for Settings, Email (read, mark read, send).
    mail_scope = ""

    def scopes(self, mail: bool = False) -> str:
        return f"{self.scope} {self.mail_scope}" if mail else self.scope

    def auth_url(self, client_id: str, redirect_uri: str, state: str, challenge: str, mail: bool = False) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.scopes(mail),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            **self.extra_auth_params(),
        }
        return f"{self.auth_endpoint}?{urlencode(params)}"

    def extra_auth_params(self) -> dict:
        return {}

    async def _token(self, form: dict) -> dict:
        async with self.client() as client:
            response = await client.post(self.token_endpoint, data=form)
        body = response.json() if response.content else {}
        if response.status_code != 200:
            code = str(body.get("error") or "")
            raise CalendarError(sign_in_problem(self.label, code, response.status_code), code)
        return body

    async def exchange(
        self, code: str, verifier: str, client_id: str, client_secret: str, redirect_uri: str, mail: bool = False,
    ) -> Tokens:
        body = await self._token({
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            **self.extra_token_params(mail),
        })
        tokens = Tokens(body["access_token"], body.get("refresh_token"))
        return Tokens(tokens.access_token, tokens.refresh_token, await self.email(tokens.access_token))

    async def refresh(self, refresh_token: str, client_id: str, client_secret: str, mail: bool = False) -> Tokens:
        body = await self._token({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            **self.extra_token_params(mail),
        })
        return Tokens(body["access_token"], body.get("refresh_token"))

    def extra_token_params(self, mail: bool = False) -> dict:
        return {}

    async def _get(self, url: str, token: str, params: dict | None = None, headers: dict | None = None) -> dict:
        async with self.client() as client:
            response = await client.get(
                url, params=params, headers={"Authorization": f"Bearer {token}", **(headers or {})},
            )
        if response.status_code != 200:
            raise CalendarError(f"{self.label} calendar answered HTTP {response.status_code}")
        return response.json()

    async def _send(self, method: str, url: str, token: str, body: dict | None = None) -> dict:
        async with self.client() as client:
            response = await client.request(method, url, json=body, headers={"Authorization": f"Bearer {token}"})
        if response.status_code in (401, 403):
            raise CalendarError(
                f"{self.label} didn't let Venus change events. Reconnect it in Settings, Calendar "
                "to give Venus permission."
            )
        if response.status_code == 404:
            raise CalendarError(f"That event isn't in your {self.label} calendar anymore.")
        if response.status_code >= 300:
            raise CalendarError(f"{self.label} calendar answered HTTP {response.status_code}")
        return response.json() if response.content else {}

    async def email(self, access_token: str) -> str | None:
        raise NotImplementedError

    async def events(self, access_token: str, start: datetime, end: datetime) -> list[Event]:
        raise NotImplementedError

    async def create(self, access_token: str, draft: EventDraft) -> str:
        """Adds the event; its new id."""
        raise NotImplementedError

    async def update(self, access_token: str, event_id: str, draft: EventDraft) -> None:
        raise NotImplementedError

    async def delete(self, access_token: str, event_id: str) -> None:
        raise NotImplementedError


# What Google and Microsoft's error codes mean for you, and what to do.
SIGN_IN_PROBLEMS = {
    "access_denied": "{label} said no. If the app is still in Testing, publish it (or add yourself as a test user) and try again.",
    "invalid_client": "{label} doesn't recognise the client ID or secret. Copy both again from your {label} app.",
    "unauthorized_client": "{label} doesn't recognise the client ID or secret. Copy both again from your {label} app.",
    "invalid_grant": "The {label} sign-in expired or was removed. Connect again.",
    "redirect_uri_mismatch": "The redirect address isn't in your {label} app. Add the one shown here and try again.",
    "consent_required": "Your {label} admin has to approve Venus first (common for uni accounts).",
    "admin_consent_required": "Your {label} admin has to approve Venus first (common for uni accounts).",
}


def sign_in_problem(label: str, code: str, status: int | None = None) -> str:
    text = SIGN_IN_PROBLEMS.get(code)
    if text:
        return text.format(label=label)
    return f"{label} sign-in didn't work ({code or f'HTTP {status}'}). Try Connect again."


def all_day_start(day: str) -> datetime:
    return datetime.combine(date.fromisoformat(day), datetime.min.time(), tzinfo=timezone.utc)


class Google(Provider):
    name = "google"
    label = "Google"
    auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    # Read every calendar, and add or change events (Settings, Calendar: reconnect after upgrading).
    scope = "https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events"
    api = "https://www.googleapis.com/calendar/v3"
    MAX_CALENDARS = 10

    # Read, mark read and send Gmail (not delete forever, not settings).
    mail_scope = "https://www.googleapis.com/auth/gmail.modify"

    def extra_auth_params(self) -> dict:
        # offline = give a refresh token; consent = give it again on reconnect;
        # include_granted_scopes = adding mail keeps the calendar permission.
        return {"access_type": "offline", "prompt": "consent", "include_granted_scopes": "true"}

    async def calendars(self, access_token: str) -> list[dict]:
        body = await self._get(f"{self.api}/users/me/calendarList", access_token, {"minAccessRole": "reader"})
        return body.get("items", [])

    async def email(self, access_token: str) -> str | None:
        primary = [c for c in await self.calendars(access_token) if c.get("primary")]
        return primary[0]["id"] if primary else None

    async def events(self, access_token: str, start: datetime, end: datetime) -> list[Event]:
        # Every calendar ticked in Google Calendar, e.g. a subscribed class timetable.
        shown = [c for c in await self.calendars(access_token) if c.get("selected") or c.get("primary")]
        events: list[Event] = []
        for calendar in shown[: self.MAX_CALENDARS]:
            # Ids like "en.malaysia#holiday@group.v.calendar.google.com": a bare # would cut the address short.
            try:
                body = await self._get(
                    f"{self.api}/calendars/{quote(calendar['id'], safe='@')}/events",
                    access_token,
                    {"timeMin": iso(start), "timeMax": iso(end), "singleEvents": "true", "orderBy": "startTime", "maxResults": "50"},
                )
            except CalendarError:
                # One calendar Google won't list (a removed subscription) shouldn't hide the others.
                continue
            for item in body.get("items", []):
                if item.get("status") == "cancelled":
                    continue
                all_day = "date" in item.get("start", {})
                if all_day:
                    begins, ends = all_day_start(item["start"]["date"]), all_day_start(item["end"]["date"])
                else:
                    begins = datetime.fromisoformat(item["start"]["dateTime"])
                    ends = datetime.fromisoformat(item["end"]["dateTime"])
                events.append(Event(
                    # The calendar too: changing an event needs both.
                    id=f"google:{calendar['id']}|{item['id']}",
                    title=item.get("summary") or "(no title)",
                    start=begins,
                    end=ends,
                    all_day=all_day,
                    source="Google",
                    location=item.get("location") or "",
                    notes=item.get("description") or "",
                    editable=calendar.get("accessRole") in ("owner", "writer"),
                ))
        return events

    @staticmethod
    def body(draft: EventDraft) -> dict:
        if draft.all_day:
            # Google's all-day end is the day after, like FullCalendar's.
            start, end = {"date": draft.start.date().isoformat()}, {"date": draft.end.date().isoformat()}
        else:
            start, end = {"dateTime": iso(draft.start)}, {"dateTime": iso(draft.end)}
        return {"summary": draft.title, "location": draft.location, "description": draft.notes, "start": start, "end": end}

    @staticmethod
    def split(event_id: str) -> tuple[str, str]:
        calendar_id, _, item_id = event_id.partition("|")
        if not calendar_id or not item_id:
            raise CalendarError("That isn't a Google event id.")
        return quote(calendar_id, safe=""), quote(item_id, safe="")

    async def create(self, access_token: str, draft: EventDraft) -> str:
        item = await self._send("POST", f"{self.api}/calendars/primary/events", access_token, self.body(draft))
        return f"primary|{item.get('id', '')}"

    async def update(self, access_token: str, event_id: str, draft: EventDraft) -> None:
        calendar_id, item_id = self.split(event_id)
        await self._send("PATCH", f"{self.api}/calendars/{calendar_id}/events/{item_id}", access_token, self.body(draft))

    async def delete(self, access_token: str, event_id: str) -> None:
        calendar_id, item_id = self.split(event_id)
        await self._send("DELETE", f"{self.api}/calendars/{calendar_id}/events/{item_id}", access_token)


def graph_time(value: dict) -> datetime:
    # Graph sends "2026-10-14T01:00:00.0000000" in the zone we asked for (UTC).
    text = value["dateTime"].split(".")[0]
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)


class Microsoft(Provider):
    name = "microsoft"
    label = "Outlook"
    # "common" = personal Outlook.com and work/school accounts both work.
    auth_endpoint = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    token_endpoint = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    # ReadWrite: add and change events from the Calendar page (reconnect after upgrading).
    scope = "offline_access User.Read Calendars.ReadWrite"
    api = "https://graph.microsoft.com/v1.0"

    def extra_auth_params(self) -> dict:
        return {"response_mode": "query"}

    mail_scope = "Mail.ReadWrite Mail.Send"

    def extra_token_params(self, mail: bool = False) -> dict:
        return {"scope": self.scopes(mail)}

    async def email(self, access_token: str) -> str | None:
        me = await self._get(f"{self.api}/me", access_token, {"$select": "mail,userPrincipalName"})
        return me.get("mail") or me.get("userPrincipalName")

    async def events(self, access_token: str, start: datetime, end: datetime) -> list[Event]:
        body = await self._get(
            f"{self.api}/me/calendarView",
            access_token,
            {
                "startDateTime": iso(start),
                "endDateTime": iso(end),
                "$select": "id,subject,start,end,location,isAllDay,isCancelled,bodyPreview,isOrganizer",
                "$orderby": "start/dateTime",
                "$top": "50",
            },
            headers={"Prefer": 'outlook.timezone="UTC"'},
        )
        events = []
        for item in body.get("value", []):
            if item.get("isCancelled"):
                continue
            events.append(Event(
                id=f"microsoft:{item['id']}",
                title=item.get("subject") or "(no title)",
                start=graph_time(item["start"]),
                end=graph_time(item["end"]),
                all_day=bool(item.get("isAllDay")),
                source="Outlook",
                location=(item.get("location") or {}).get("displayName") or "",
                notes=item.get("bodyPreview") or "",
                editable=True,
            ))
        return events

    @staticmethod
    def body(draft: EventDraft) -> dict:
        def when(moment: datetime) -> dict:
            return {"dateTime": moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": "UTC"}

        return {
            "subject": draft.title,
            "body": {"contentType": "text", "content": draft.notes},
            "start": when(draft.start),
            "end": when(draft.end),
            "isAllDay": draft.all_day,
            "location": {"displayName": draft.location},
        }

    async def create(self, access_token: str, draft: EventDraft) -> str:
        item = await self._send("POST", f"{self.api}/me/events", access_token, self.body(draft))
        return str(item.get("id", ""))

    async def update(self, access_token: str, event_id: str, draft: EventDraft) -> None:
        await self._send("PATCH", f"{self.api}/me/events/{quote(event_id, safe='')}", access_token, self.body(draft))

    async def delete(self, access_token: str, event_id: str) -> None:
        await self._send("DELETE", f"{self.api}/me/events/{quote(event_id, safe='')}", access_token)


PROVIDERS: dict[str, type[Provider]] = {"google": Google, "microsoft": Microsoft}

# How long a started sign-in may take before its state is forgotten.
STATE_LIFETIME = timedelta(minutes=10)
