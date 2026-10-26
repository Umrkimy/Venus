from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from config import CoreSettings, get_settings
from features.auth.dependencies import require_owner, require_owner_or_node
from features.calendar.dependencies import get_calendar_repository, get_calendar_service, get_sign_ins
from features.calendar.ics import MAX_BYTES, check_ics, fetch_ics, ics_events
from features.calendar.providers import PROVIDERS, CalendarError, Event, EventDraft, pkce_pair, sign_in_problem
from features.calendar.repository import CalendarRepository, DuplicateNameError
from features.calendar.service import CalendarService, SignIns, due_soon
from features.email.dependencies import get_email_repository
from features.email.repository import DuplicateAccountError, EmailRepository
from features.settings.router import encrypt_key
from features.settings.secrets import decrypt_text, encrypt_text

router = APIRouter(prefix="/calendar")

ProviderName = Literal["google", "microsoft"]
SETTINGS_PAGE = "/settings/calendar"


class CalendarClientRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=1, max_length=200)
    # Empty keeps the saved one.
    client_secret: str | None = Field(default=None, max_length=500)


class IcsCalendarRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    # A link Venus re-reads, or the text of an uploaded .ics file.
    url: str | None = Field(default=None, max_length=2000)
    content: str | None = Field(default=None, max_length=MAX_BYTES)

    @model_validator(mode="after")
    def link_or_file(self) -> "IcsCalendarRequest":
        if bool(self.url) == bool(self.content):
            raise ValueError("Give a link or a file, not both")
        return self


def redirect_uri(request: Request, provider: str) -> str:
    """Where Google or Microsoft sends the browser back: the address you opened Venus at."""
    host = request.headers.get("x-forwarded-host", "").split(",")[0].strip() or request.headers.get("host", "")
    proto = request.headers.get("x-forwarded-proto", "").split(",")[0].strip() or request.url.scheme
    return f"{proto}://{host}/api/calendar/{provider}/callback"


def event_json(event: Event) -> dict:
    return {
        "id": event.id,
        "title": event.title,
        "start": event.start.isoformat(),
        "end": event.end.isoformat(),
        "all_day": event.all_day,
        "source": event.source,
        "location": event.location,
        "notes": event.notes,
        "editable": event.editable,
    }


# A year and a bit: the widest view the Calendar page asks for, with room.
MAX_RANGE = timedelta(days=400)


class EventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    start: datetime
    end: datetime
    all_day: bool = False
    location: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=5000)

    @model_validator(mode="after")
    def sensible_times(self) -> "EventRequest":
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Times need a time zone")
        if self.end < self.start:
            raise ValueError("The event ends before it starts")
        if self.end - self.start > MAX_RANGE:
            raise ValueError("An event can't be longer than a year")
        return self

    def draft(self) -> EventDraft:
        return EventDraft(self.title, self.start, self.end, self.all_day, self.location.strip(), self.notes)


class NewEventRequest(EventRequest):
    # venus, google or microsoft
    calendar: str = Field(default="venus", pattern=r"^(venus|google|microsoft)$")


def calendar_problem(exc: CalendarError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def back_to_settings(**query: str) -> RedirectResponse:
    return RedirectResponse(f"{SETTINGS_PAGE}?{urlencode(query)}", status_code=status.HTTP_303_SEE_OTHER)


def back_to_email(**query: str) -> RedirectResponse:
    return RedirectResponse(f"/settings/email?{urlencode(query)}", status_code=status.HTTP_303_SEE_OTHER)


def signed_out(account) -> str | None:
    moment = account.signed_out_at if account else None
    if moment is None:
        return None
    # SQLite (tests) drops the zone; it was saved in UTC.
    return (moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)).isoformat()


@router.get("", dependencies=[Depends(require_owner)])
def list_calendars(
    request: Request,
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
):
    saved = {account.provider: account for account in repository.list_all()}
    return [
        {
            "provider": name,
            "label": provider.label,
            "client_id": saved[name].client_id if name in saved else None,
            "configured": name in saved,
            "connected": bool(name in saved and saved[name].refresh_token_encrypted and not saved[name].signed_out_at),
            "signed_out_at": signed_out(saved.get(name)),
            "email": saved[name].account_email if name in saved else None,
            "mail": bool(name in saved and saved[name].mail),
            "redirect_uri": redirect_uri(request, name),
        }
        for name, provider in PROVIDERS.items()
    ]


# Fixed paths first, so "events" and "upcoming" are never read as a provider name.
@router.get("/events", dependencies=[Depends(require_owner)])
async def events(
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    start: datetime | None = None,
    end: datetime | None = None,
):
    """The coming week (cached), or every event from start to end (the Calendar page)."""
    if start is None or end is None:
        found, errors = await service.events()
    else:
        if start.tzinfo is None or end.tzinfo is None or not start < end <= start + MAX_RANGE:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Pick a start and end with a time zone, at most 400 days apart")
        found, errors = await service.between(start, end)
    return {"events": [event_json(event) for event in found], "errors": errors}


@router.get("/writable", dependencies=[Depends(require_owner)])
def writable(service: Annotated[CalendarService, Depends(get_calendar_service)]):
    """Where a new event can go: Venus, then connected Google/Outlook."""
    return service.writable()


@router.post("/events", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_owner)])
async def add_event(body: NewEventRequest, service: Annotated[CalendarService, Depends(get_calendar_service)]):
    try:
        return {"id": await service.create(body.calendar, body.draft())}
    except CalendarError as exc:
        raise calendar_problem(exc) from exc


@router.patch("/events/{event_id:path}", dependencies=[Depends(require_owner)])
async def change_event(
    event_id: str, body: EventRequest, service: Annotated[CalendarService, Depends(get_calendar_service)],
):
    try:
        await service.update(event_id, body.draft())
    except CalendarError as exc:
        raise calendar_problem(exc) from exc
    return {"id": event_id}


@router.delete("/events/{event_id:path}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_owner)])
async def delete_event(event_id: str, service: Annotated[CalendarService, Depends(get_calendar_service)]):
    try:
        await service.delete(event_id)
    except CalendarError as exc:
        raise calendar_problem(exc) from exc


@router.get("/upcoming", dependencies=[Depends(require_owner_or_node)])
async def upcoming(
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    minutes: Annotated[int, Query(ge=1, le=60)] = 10,
):
    """For the PC's reminder pop-ups: timed events starting in the next few minutes."""
    found, _ = await service.events()
    return [event_json(event) for event in due_soon(found, datetime.now(timezone.utc), minutes)]


@router.get("/ics", dependencies=[Depends(require_owner)])
def list_ics(repository: Annotated[CalendarRepository, Depends(get_calendar_repository)]):
    # The link stays in Core (it can hold a private key): only whether it's a link or a file.
    return [
        {"id": str(calendar.id), "name": calendar.name, "kind": "link" if calendar.url_encrypted else "file"}
        for calendar in repository.list_ics()
    ]


@router.post("/ics", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_owner)])
async def add_ics(
    body: IcsCalendarRequest,
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
):
    """Check it reads, save it, and say how many events the next 4 weeks have."""
    try:
        text = await fetch_ics(body.url, service.transport) if body.url else check_ics(body.content)
        now = datetime.now(timezone.utc)
        coming = ics_events(text, now, now + timedelta(days=28), body.name, service.zone)
    except CalendarError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="That calendar file couldn't be read.",
        ) from exc
    try:
        calendar = repository.add_ics(
            body.name,
            datetime.now(timezone.utc),
            url_encrypted=encrypt_key(body.url.strip(), settings) if body.url else None,
            content=None if body.url else text,
        )
    except DuplicateNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have a calendar with that name") from exc
    service.forget()
    return {
        "id": str(calendar.id),
        "name": calendar.name,
        "kind": "link" if body.url else "file",
        "events_next_4_weeks": len(coming),
    }


@router.delete("/ics/{calendar_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_owner)])
def delete_ics(
    calendar_id: UUID,
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
):
    if not repository.delete_ics(calendar_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such calendar")
    service.forget()


@router.put("/{provider}", dependencies=[Depends(require_owner)])
def save_client(
    provider: ProviderName,
    body: CalendarClientRequest,
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
):
    try:
        repository.save_client(provider, body.client_id.strip(), encrypt_key(body.client_secret, settings))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    service.forget()
    return {"provider": provider, "configured": True}


@router.get("/{provider}/connect", dependencies=[Depends(require_owner)])
def connect(
    provider: ProviderName,
    request: Request,
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    sign_ins: Annotated[SignIns, Depends(get_sign_ins)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    mail: bool = False,
    name: Annotated[str, Query(max_length=100)] = "",
):
    """Off to Google or Microsoft. mail=true (from Settings, Email) also asks for mail."""
    account = repository.get(provider)
    if account is None:
        if mail:
            return back_to_email(error="First save the Google or Microsoft app in Settings, Calendar (the same app does both).")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Save the client id and secret first")
    verifier, challenge = pkce_pair()
    uri = redirect_uri(request, provider)
    # Reconnecting the calendar never takes mail away again.
    with_mail = mail or bool(account.mail)
    state = sign_ins.start(provider, verifier, uri, mail=with_mail, name=" ".join(name.split()))
    url = service.provider(provider).auth_url(account.client_id, uri, state, challenge, mail=with_mail)
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/{provider}/callback", dependencies=[Depends(require_owner)])
async def callback(
    provider: ProviderName,
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    sign_ins: Annotated[SignIns, Depends(get_sign_ins)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    emails: Annotated[EmailRepository, Depends(get_email_repository)],
    state: Annotated[str, Query(max_length=200)] = "",
    code: Annotated[str, Query(max_length=4000)] = "",
    error: Annotated[str, Query(max_length=200)] = "",
):
    pending = sign_ins.finish(state, provider)
    if pending is None:
        # Not a sign-in this Venus started (or it took over 10 minutes).
        return back_to_settings(error="That sign-in expired or wasn't started here. Try Connect again.")
    if error or not code:
        label = PROVIDERS[provider].label
        back = back_to_email if pending.mail else back_to_settings
        return back(error=sign_in_problem(label, error) if error else f"{label} didn't send a sign-in code. Try again.")
    account = repository.get(provider)
    if account is None:
        return back_to_settings(error="Save the client id and secret first")
    back = back_to_email if pending.mail and not account.mail else back_to_settings
    try:
        tokens = await service.provider(provider).exchange(
            code,
            pending.verifier,
            account.client_id,
            decrypt_text(account.client_secret_encrypted, settings.secret_key),
            pending.redirect_uri,
            mail=pending.mail,
        )
    except CalendarError as exc:
        return back(error=str(exc))
    if not tokens.refresh_token:
        return back(error="No refresh token came back. Remove Venus's access in your account and connect again.")
    repository.connect(
        provider,
        encrypt_text(tokens.refresh_token, settings.secret_key),
        tokens.email,
        datetime.now(timezone.utc),
        mail=pending.mail,
    )
    service.forget()
    if pending.mail and tokens.email:
        try:
            emails.add_signed_in(provider, tokens.email, pending.name or tokens.email.split("@")[0], datetime.now(timezone.utc))
        except DuplicateAccountError:
            return back(error=f"{tokens.email} is already added with an app password. Remove that one first.")
    return back(connected=provider)


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_owner)])
def disconnect(
    provider: ProviderName,
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    emails: Annotated[EmailRepository, Depends(get_email_repository)],
):
    if not repository.disconnect(provider):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not set up")
    # Its mail went through the same sign-in.
    emails.delete_signed_in(provider)
    service.forget()
