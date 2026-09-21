import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from config import CoreSettings, get_settings
from features.commands.result_registry import (
    CommandResultRegistry,
    get_command_result_registry,
)


router = APIRouter()


@router.get("/commands/{command_id}/result")
async def get_command_result(
    command_id: UUID,
    request: Request,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
):
    authorization = request.headers.get("authorization", "")
    expected_authorization = f"Bearer {settings.dev_owner_token}"

    if not hmac.compare_digest(authorization, expected_authorization):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid development owner token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = result_registry.get(command_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Command result not found",
        )

    return result.model_dump(mode="json")