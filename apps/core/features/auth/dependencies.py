from datetime import datetime, timezone
import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.engine import Engine

from config import CoreSettings, get_settings
from features.auth.models.node_device import NodeDevice
from features.auth.models.owner_account import OwnerAccount
from features.auth.repository import AuthRepository
from storage.database import get_database_engine

SESSION_COOKIE_NAME = "venus_session"


def get_auth_repository(
    engine: Annotated[Engine, Depends(get_database_engine)]
) -> AuthRepository:
    return AuthRepository(engine)


def get_current_owner(
    request: Request,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> OwnerAccount:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    owner = None
    if token is not None:
        owner = repository.get_owner_for_session(token, datetime.now(timezone.utc))
    if owner is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    return owner


def require_owner(
    request: Request,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> None:
    # Check the dev token first so token-only requests never query the database.
    # An empty token means it is switched off, so "Bearer " alone never passes.
    authorization = request.headers.get("authorization", "")
    if settings.dev_owner_token and hmac.compare_digest(
        authorization, f"Bearer {settings.dev_owner_token}"
    ):
        return

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token is not None:
        owner = repository.get_owner_for_session(token, datetime.now(timezone.utc))
        if owner is not None:
            return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_owner_or_node(
    request: Request,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> None:
    # The Node's "Hey Venus" loop speaks for the owner sitting at that PC:
    # it may hear, talk and chat, but not touch settings, keys or memories.
    device = node_device_for_header(
        request.headers.get("authorization", ""), settings, repository
    )
    if device is None:
        require_owner(request, settings, repository)
        return
    # A Node may only chat as itself, never as another PC.
    path_device_id = request.path_params.get("device_id")
    if path_device_id is not None and path_device_id != device.device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This token belongs to another device",
        )


def node_device_for_header(
    authorization: str,
    settings: CoreSettings,
    repository: AuthRepository,
) -> NodeDevice | None:
    scheme, _, token = authorization.partition(" ")
    if scheme != "Bearer" or not token:
        return None
    return repository.find_node_device(
        token, settings.dev_node_token, datetime.now(timezone.utc)
    )
