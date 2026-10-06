from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from features.auth.dependencies import get_auth_repository, require_owner
from features.auth.models.node_device import NodeDevice
from features.auth.repository import ActiveDeviceError, AuthRepository, MainDeviceError
from features.nodes.connection_registry import (
    NodeConnectionRegistry,
    get_connection_registry,
)
from features.nodes.schemas import NewDeviceRequest


router = APIRouter(prefix="/devices", dependencies=[Depends(require_owner)])


def device_json(device: NodeDevice, connected: set[str]) -> dict:
    # Never the token or its hash: the token is shown once, at creation.
    return {
        "id": str(device.id),
        "name": device.name,
        "device_id": device.device_id,
        "created_at": device.created_at.isoformat(),
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "revoked_at": device.revoked_at.isoformat() if device.revoked_at else None,
        "main": device.is_main,
        "connected": device.revoked_at is None and device.device_id in connected,
    }


@router.get("")
def list_devices(
    auth: Annotated[AuthRepository, Depends(get_auth_repository)],
    registry: Annotated[NodeConnectionRegistry, Depends(get_connection_registry)],
):
    connected = set(registry.connected_device_ids())
    return [device_json(device, connected) for device in auth.list_node_devices()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_device(
    request: NewDeviceRequest,
    auth: Annotated[AuthRepository, Depends(get_auth_repository)],
):
    device, token = auth.create_node_device(request.name, datetime.now(timezone.utc))
    return {**device_json(device, set()), "token": token}


@router.post("/{device_uuid}/revoke")
async def revoke_device(
    device_uuid: UUID,
    auth: Annotated[AuthRepository, Depends(get_auth_repository)],
    registry: Annotated[NodeConnectionRegistry, Depends(get_connection_registry)],
):
    try:
        device = auth.revoke_node_device(device_uuid, datetime.now(timezone.utc))
    except MainDeviceError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The main PC can't be revoked; change its token in .env instead",
        )
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    if device.device_id is not None:
        await registry.disconnect(device.device_id)
    return device_json(device, set())


@router.delete("/{device_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_uuid: UUID,
    auth: Annotated[AuthRepository, Depends(get_auth_repository)],
):
    try:
        deleted = auth.delete_node_device(device_uuid)
    except ActiveDeviceError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Revoke the device before deleting it",
        )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
