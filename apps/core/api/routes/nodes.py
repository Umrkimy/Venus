import hmac
from json import JSONDecodeError
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, status
from pydantic import ValidationError

from connection_registry import (
    NodeConnectionRegistry,
    get_connection_registry,
)
from config import CoreSettings, get_settings
from venus_protocol.schemas.connections import NodeHello

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
):
    authorization = websocket.headers.get("authorization", "")
    expected_authorization = f"Bearer {settings.dev_node_token}"

    if not hmac.compare_digest(authorization, expected_authorization):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    try:
        hello_payload = await websocket.receive_json()
        hello = NodeHello.model_validate(hello_payload)
    except (JSONDecodeError, ValidationError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await registry.register(hello.device_id, websocket)

    try:
        await websocket.send_json(hello.model_dump())

        message = await websocket.receive()

        if message["type"] == "websocket.disconnect":
            return

        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    finally:
        await registry.unregister(hello.device_id, websocket)
