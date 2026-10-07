from datetime import datetime, timezone
from typing import Annotated

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from features.auth.dependencies import (
    SESSION_COOKIE_NAME,
    get_auth_repository,
    get_current_owner,
    require_owner,
)
from features.auth.models.owner_session import OwnerSession
from features.auth.models.owner_account import OwnerAccount
from features.auth.passwords import hash_password, verify_password
from features.auth.rate_limit import (
    LoginRateLimiter,
    client_key as login_client_key,
    get_login_rate_limiter,
)
from features.auth.repository import SESSION_MAX_AGE, AuthRepository
from features.auth.schemas import LoginRequest, OwnerResponse


router = APIRouter(prefix="/auth")

_DUMMY_HASH = hash_password("venus-dummy-password")


def _request_is_https(request: Request) -> bool:
    # Over Tailscale the browser speaks HTTPS, but Core only sees plain http
    # from the proxy in front of it, so trust the first X-Forwarded-Proto.
    # A faked header can only make the cookie stricter, never weaker.
    forwarded = request.headers.get("x-forwarded-proto", "")
    first = forwarded.split(",")[0].strip().lower()
    return first == "https" or request.url.scheme == "https"


@router.post("/login")
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
    limiter: Annotated[LoginRateLimiter, Depends(get_login_rate_limiter)],
) -> OwnerResponse:
    now = datetime.now(timezone.utc)
    client_key = login_client_key(request)

    if limiter.is_blocked(client_key, now):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts",
        )

    owner = repository.get_owner_by_username(body.username)
    password_hash_value = owner.password_hash if owner else _DUMMY_HASH
    password_ok = verify_password(body.password, password_hash_value)

    if owner is None or not password_ok:
        limiter.record_failure(client_key, now)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    limiter.reset(client_key)
    repository.delete_expired_sessions(owner.account_id, now)
    token = repository.create_session(
        owner.account_id, now, request.headers.get("user-agent")
    )
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=int(SESSION_MAX_AGE.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=_request_is_https(request),
    )
    return OwnerResponse(username=owner.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> None:
    token = request.cookies.get(SESSION_COOKIE_NAME)

    if token is not None:
        repository.delete_session(token)

    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.get("/me")
def me(
    owner: Annotated[OwnerAccount, Depends(get_current_owner)],
) -> OwnerResponse:
    return OwnerResponse(username=owner.username)


def session_json(owner_session: OwnerSession, current_id: UUID | None) -> dict:
    return {
        "id": str(owner_session.id),
        "user_agent": owner_session.user_agent,
        "created_at": owner_session.created_at.isoformat(),
        "last_seen_at": (
            owner_session.last_seen_at.isoformat() if owner_session.last_seen_at else None
        ),
        "current": owner_session.id == current_id,
    }


def _current_session_id(request: Request, repository: AuthRepository) -> UUID | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return repository.session_id_for_token(token) if token else None


@router.get("/sessions", dependencies=[Depends(require_owner)])
def list_sessions(
    request: Request,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
):
    current_id = _current_session_id(request, repository)
    return [
        session_json(owner_session, current_id)
        for owner_session in repository.list_sessions(datetime.now(timezone.utc))
    ]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_owner)],
)
def sign_out_session(
    session_id: UUID,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> None:
    if not repository.delete_session_by_id(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )


@router.post("/sessions/sign-out-others", dependencies=[Depends(require_owner)])
def sign_out_others(
    request: Request,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
):
    # For a lost phone: everything except the browser asking ends now.
    signed_out = repository.delete_other_sessions(request.cookies.get(SESSION_COOKIE_NAME))
    return {"signed_out": signed_out}
