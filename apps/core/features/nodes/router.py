from datetime import datetime, timedelta, timezone
import hmac
from json import JSONDecodeError
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, status
from pydantic import ValidationError
from starlette.websockets import WebSocketDisconnect

from venus_protocol.schemas.commands import (
    CommandResult,
    OpenApplicationCommand,
)
from venus_protocol.schemas.connections import NodeHello

from features.commands.result_registry import (
    CommandResultRegistry,
    get_command_result_registry,
)
from features.commands.dependencies import get_command_record_repository
from features.commands.models.command_record import CommandRecord
from features.commands.repository import CommandRecordRepository
from features.nodes.connection_registry import (
    NodeConnectionRegistry,
    get_connection_registry,
)
from config import CoreSettings, get_settings


router = APIRouter()

@router.get("/nodes/{device_id}/connection")
async def get_node_connection_status(
    device_id: str,
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
):
    return {
        "device_id": device_id,
        "connected": registry.get(device_id) is not None,
    }


@router.websocket("/nodes/connect")
async def connect_node(
    websocket: WebSocket,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
    result_registry: Annotated[
        CommandResultRegistry,
        Depends(get_command_result_registry),
    ],
    command_records: Annotated[
        CommandRecordRepository,
        Depends(get_command_record_repository),
    ],
):
    authorization = websocket.headers.get("authorization", "")
    expected_authorization = f"Bearer {settings.dev_node_token}"

    # Compare secrets safely even when an attacker controls the header.
    if not hmac.compare_digest(authorization, expected_authorization):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        hello_payload = await websocket.receive_json()
        hello = NodeHello.model_validate(hello_payload)
    except WebSocketDisconnect:
        return
    except (JSONDecodeError, KeyError, ValidationError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await registry.register(hello.device_id, websocket)

    try:
        await websocket.send_json(hello.model_dump())

        while True:
            try:
                result_payload = await websocket.receive_json()
                result = CommandResult.model_validate(result_payload)
            except WebSocketDisconnect:
                return
            except (JSONDecodeError, KeyError, ValidationError):
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            accepted = result_registry.accept_result(
                result,
                hello.device_id,
                websocket,
            )

            if not accepted:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            command_records.complete(
                command_id=result.command_id,
                state=result.status,
                detail=result.detail,
                completed_at=datetime.now(timezone.utc),
            )
    finally:
        await registry.unregister(hello.device_id, websocket)


@router.post("/nodes/{device_id}/commands/fake")
async def send_fake_command(
    device_id: str,
    request: Request,
    settings: Annotated[CoreSettings, Depends(get_settings)],
    registry: Annotated[
        NodeConnectionRegistry,
        Depends(get_connection_registry),
    ],
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

    websocket = registry.get(device_id)

    if websocket is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node is not connected",
        )

    command = OpenApplicationCommand(
        command_id=uuid4(),
        device_id=device_id,
        application_id="spotify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    # Save first so a sent command always has a durable Core record.
    command_records.create(
        CommandRecord(
            command_id=command.command_id,
            device_id=command.device_id,
            application_id=command.application_id,
            expires_at=command.expires_at,
        )
    )
    result_registry.expect(command, websocket)
    await websocket.send_json(command.model_dump(mode="json"))

    return command.model_dump(mode="json")
