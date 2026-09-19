import hmac
from typing import Annotated
from pydantic import ValidationError
from json import JSONDecodeError

from fastapi import APIRouter, Depends, WebSocket, status
from config import CoreSettings, get_settings


from venus_protocol.schemas.connections import NodeHello

router = APIRouter()


@router.websocket("/nodes/connect")
async def connect_node(
    websocket: WebSocket,
    settings: Annotated[CoreSettings, Depends(get_settings)],
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

    await websocket.send_json(hello.model_dump())