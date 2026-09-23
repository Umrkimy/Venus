from datetime import datetime, timezone
import hmac
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from config import CoreSettings, get_settings
from features.commands.result_registry import (
    CommandResultRegistry,
    get_command_result_registry,
)
from features.commands.dependencies import get_command_record_repository
from features.commands.repository import CommandRecordRepository

from venus_protocol.schemas.commands import CommandResult


router = APIRouter()


@router.get("/commands/{command_id}")
async def get_command_status(
    command_id: UUID,
    request: Request,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
    command_records: Annotated[
        CommandRecordRepository,
        Depends(get_command_record_repository),
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

    if result is not None:
        return result.model_dump(mode="json")

    if result_registry.is_expired(command_id):
        return {
            "command_id": str(command_id),
            "status": "unknown",
        }

    if result_registry.is_dispatched(command_id):
        return {
            "command_id": str(command_id),
            "status": "dispatched",
        }

    record = command_records.get(command_id)

    if record is not None:
        expires_at = record.expires_at

        # SQLite drops timezone information in tests; PostgreSQL keeps it.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= datetime.now(timezone.utc):
            if record.state == "awaiting_approval":
                return {
                    "command_id": str(record.command_id),
                    "status": "expired",
                }
            if record.state == "dispatched":
                return {
                    "command_id": str(record.command_id),
                    "status": "unknown",
                }

        response = {
            "command_id": str(record.command_id),
            "status": record.state,
        }
        if record.detail is not None:
            response["detail"] = record.detail

        return response

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Command not found",
    )


@router.get("/commands/{command_id}/result")
async def get_command_result(
    command_id: UUID,
    request: Request,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
    command_records: Annotated[
        CommandRecordRepository,
        Depends(get_command_record_repository),
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

    if result is not None:
        return result.model_dump(mode="json")

    record = command_records.get(command_id)

    if record is not None and record.completed_at is not None:
        return CommandResult(
            command_id=record.command_id,
            status=record.state,
            detail=record.detail,
        ).model_dump(mode="json")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Command result not found",
    )
