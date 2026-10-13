from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from config import CoreSettings, get_settings
from features.auth.dependencies import require_owner, require_owner_or_node
from features.calendar.dependencies import get_calendar_repository, get_calendar_service, get_sign_ins
from features.calendar.providers import PROVIDERS, CalendarError, Event, pkce_pair
from features.calendar.repository import CalendarRepository
from features.calendar.service import CalendarService, SignIns, due_soon
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
    }


def back_to_settings(**query: str) -> RedirectResponse:
    return RedirectResponse(f"{SETTINGS_PAGE}?{urlencode(query)}", status_code=status.HTTP_303_SEE_OTHER)


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
            "connected": bool(name in saved and saved[name].refresh_token_encrypted),
            "email": saved[name].account_email if name in saved else None,
            "redirect_uri": redirect_uri(request, name),
        }
        for name, provider in PROVIDERS.items()
    ]


# Fixed paths first, so "events" and "upcoming" are never read as a provider name.
@router.get("/events", dependencies=[Depends(require_owner)])
async def events(service: Annotated[CalendarService, Depends(get_calendar_service)]):
    found, errors = await service.events()
    return {"events": [event_json(event) for event in found], "errors": errors}


@router.get("/upcoming", dependencies=[Depends(require_owner_or_node)])
async def upcoming(
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    minutes: Annotated[int, Query(ge=1, le=60)] = 10,
):
    """For the PC's reminder pop-ups: timed events starting in the next few minutes."""
    found, _ = await service.events()
    return [event_json(event) for event in due_soon(found, datetime.now(timezone.utc), minutes)]


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
):
    account = repository.get(provider)
    if account is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Save the client id and secret first")
    verifier, challenge = pkce_pair()
    uri = redirect_uri(request, provider)
    state = sign_ins.start(provider, verifier, uri)
    url = service.provider(provider).auth_url(account.client_id, uri, state, challenge)
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/{provider}/callback", dependencies=[Depends(require_owner)])
async def callback(
    provider: ProviderName,
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    sign_ins: Annotated[SignIns, Depends(get_sign_ins)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    state: Annotated[str, Query(max_length=200)] = "",
    code: Annotated[str, Query(max_length=4000)] = "",
    error: Annotated[str, Query(max_length=200)] = "",
):
    pending = sign_ins.finish(state, provider)
    if pending is None:
        # Not a sign-in this Venus started (or it took over 10 minutes).
        return back_to_settings(error="That sign-in expired or wasn't started here. Try Connect again.")
    if error or not code:
        return back_to_settings(error=f"Sign-in was cancelled ({error or 'no code'}).")
    account = repository.get(provider)
    if account is None:
        return back_to_settings(error="Save the client id and secret first")
    try:
        tokens = await service.provider(provider).exchange(
            code,
            pending.verifier,
            account.client_id,
            decrypt_text(account.client_secret_encrypted, settings.secret_key),
            pending.redirect_uri,
        )
    except CalendarError as exc:
        return back_to_settings(error=str(exc))
    if not tokens.refresh_token:
        return back_to_settings(
            error="No refresh token came back. Remove Venus's access in your account and connect again."
        )
    repository.connect(
        provider,
        encrypt_text(tokens.refresh_token, settings.secret_key),
        tokens.email,
        datetime.now(timezone.utc),
    )
    service.forget()
    return back_to_settings(connected=provider)


@router.delete("/{provider}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_owner)])
def disconnect(
    provider: ProviderName,
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
):
    if not repository.disconnect(provider):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not set up")
    service.forget()
