from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from features.auth.dependencies import (
    SESSION_COOKIE_NAME,
    get_auth_repository,
    get_current_owner,
)
from features.auth.models.owner_account import OwnerAccount
from features.auth.passwords import hash_password, verify_password
from features.auth.rate_limit import LoginRateLimiter, get_login_rate_limiter
from features.auth.repository import SESSION_LIFETIME, AuthRepository
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
    client_key = request.client.host if request.client else "unknown"

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
    token = repository.create_session(owner.account_id, now)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
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