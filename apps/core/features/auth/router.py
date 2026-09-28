from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from features.auth.dependencies import (
    SESSION_COOKIE_NAME,
    get_auth_repository,
    get_current_owner,
)
from features.auth.models.owner_account import OwnerAccount
from features.auth.passwords import verify_password
from features.auth.repository import SESSION_LIFETIME, AuthRepository
from features.auth.schemas import LoginRequest, OwnerResponse


router = APIRouter(prefix="/auth")


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> OwnerResponse:
    owner = repository.get_owner_by_username(body.username)

    if owner is None or not verify_password(body.password, owner.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = repository.create_session(owner.account_id, datetime.now(timezone.utc))
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
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