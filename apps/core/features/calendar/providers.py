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
from urllib.parse import urlencode

import httpx2


class CalendarError(Exception):
    """Google or Microsoft said no; the message is safe to show."""


@dataclass(frozen=True)
class Event:
    id: str
    title: str
    start: datetime  # Timezone-aware; all-day events start at midnight UTC of that day.
    end: datetime
    all_day: bool
    source: str  # "Google" or "Outlook"
    location: str = ""


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

    def auth_url(self, client_id: str, redirect_uri: str, state: str, challenge: str) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.scope,
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
            # invalid_grant = the sign-in was revoked or expired: connect again.
            reason = body.get("error_description") or body.get("error") or f"HTTP {response.status_code}"
            raise CalendarError(f"{self.label} sign-in failed: {str(reason)[:200]}")
        return body

    async def exchange(self, code: str, verifier: str, client_id: str, client_secret: str, redirect_uri: str) -> Tokens:
        body = await self._token({
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": verifier,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            **self.extra_token_params(),
        })
        tokens = Tokens(body["access_token"], body.get("refresh_token"))
        return Tokens(tokens.access_token, tokens.refresh_token, await self.email(tokens.access_token))

    async def refresh(self, refresh_token: str, client_id: str, client_secret: str) -> Tokens:
        body = await self._token({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            **self.extra_token_params(),
        })
        return Tokens(body["access_token"], body.get("refresh_token"))

    def extra_token_params(self) -> dict:
        return {}

    async def _get(self, url: str, token: str, params: dict | None = None, headers: dict | None = None) -> dict:
        async with self.client() as client:
            response = await client.get(
                url, params=params, headers={"Authorization": f"Bearer {token}", **(headers or {})},
            )
        if response.status_code != 200:
            raise CalendarError(f"{self.label} calendar answered HTTP {response.status_code}")
        return response.json()

    async def email(self, access_token: str) -> str | None:
        raise NotImplementedError

    async def events(self, access_token: str, start: datetime, end: datetime) -> list[Event]:
        raise NotImplementedError


def all_day_start(day: str) -> datetime:
    return datetime.combine(date.fromisoformat(day), datetime.min.time(), tzinfo=timezone.utc)


class Google(Provider):
    name = "google"
    label = "Google"
    auth_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    scope = "https://www.googleapis.com/auth/calendar.readonly"
    api = "https://www.googleapis.com/calendar/v3"
    MAX_CALENDARS = 10

    def extra_auth_params(self) -> dict:
        # offline = give a refresh token; consent = give it again on reconnect.
        return {"access_type": "offline", "prompt": "consent"}

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
            body = await self._get(
                f"{self.api}/calendars/{calendar['id']}/events",
                access_token,
                {"timeMin": iso(start), "timeMax": iso(end), "singleEvents": "true", "orderBy": "startTime", "maxResults": "50"},
            )
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
                    id=f"google:{item['id']}",
                    title=item.get("summary") or "(no title)",
                    start=begins,
                    end=ends,
                    all_day=all_day,
                    source="Google",
                    location=item.get("location") or "",
                ))
        return events


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
    scope = "offline_access User.Read Calendars.Read"
    api = "https://graph.microsoft.com/v1.0"

    def extra_auth_params(self) -> dict:
        return {"response_mode": "query"}

    def extra_token_params(self) -> dict:
        return {"scope": self.scope}

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
                "$select": "id,subject,start,end,location,isAllDay,isCancelled",
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
            ))
        return events


PROVIDERS: dict[str, type[Provider]] = {"google": Google, "microsoft": Microsoft}

# How long a started sign-in may take before its state is forgotten.
STATE_LIFETIME = timedelta(minutes=10)
