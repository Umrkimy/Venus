from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

import httpx2
from fastapi import APIRouter, Depends, HTTPException, status

from config import CoreSettings, get_settings
from features.auth.dependencies import require_owner
from features.home.assistant import AssistantError, list_entities
from features.home.dependencies import get_home_assistant_transport, get_home_device_repository
from features.home.models.home_device import HomeDevice
from features.home.repository import DuplicateNameError, HomeDeviceRepository
from features.home.schemas import HomeAssistantRequest, HomeDeviceRequest
from features.settings.router import encrypt_key
from features.settings.secrets import decrypt_text

router = APIRouter(prefix="/home", dependencies=[Depends(require_owner)])


def device_json(device: HomeDevice) -> dict:
    # The Tuya key never leaves Core: only whether one is saved.
    return {
        "id": str(device.id),
        "name": device.name,
        "kind": device.kind,
        "address": device.address,
        "mac": device.mac,
        "tuya_id": device.tuya_id,
        "tuya_version": device.tuya_version,
        "has_key": device.local_key_encrypted is not None,
        "ha_entity_id": device.ha_entity_id,
    }


@router.get("/devices")
def list_devices(devices: Annotated[HomeDeviceRepository, Depends(get_home_device_repository)]):
    return [device_json(device) for device in devices.list_all()]


@router.post("/devices", status_code=status.HTTP_201_CREATED)
def add_device(
    request: HomeDeviceRequest,
    devices: Annotated[HomeDeviceRepository, Depends(get_home_device_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
):
    if request.ha_entity_id and devices.get_assistant() is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connect Home Assistant first")
    try:
        device = devices.add(
            name=request.name,
            kind=request.kind,
            now=datetime.now(timezone.utc),
            address=request.address,
            mac=request.mac,
            tuya_id=request.tuya_id,
            local_key_encrypted=encrypt_key(request.local_key, settings),
            tuya_version=request.tuya_version,
            ha_entity_id=request.ha_entity_id,
        )
    except DuplicateNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a device with that name",
        ) from exc
    return device_json(device)


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: UUID,
    devices: Annotated[HomeDeviceRepository, Depends(get_home_device_repository)],
):
    if not devices.delete(device_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such device")


@router.get("/assistant")
def get_assistant(devices: Annotated[HomeDeviceRepository, Depends(get_home_device_repository)]):
    # The token never leaves Core: only whether one is saved.
    row = devices.get_assistant()
    return {"url": row.url if row else None, "connected": row is not None}


@router.put("/assistant")
def save_assistant(
    request: HomeAssistantRequest,
    devices: Annotated[HomeDeviceRepository, Depends(get_home_device_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
):
    if request.token is None and devices.get_assistant() is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Paste the access token")
    devices.set_assistant(request.url, encrypt_key(request.token, settings))
    return {"url": request.url, "connected": True}


@router.delete("/assistant", status_code=status.HTTP_204_NO_CONTENT)
def forget_assistant(devices: Annotated[HomeDeviceRepository, Depends(get_home_device_repository)]):
    devices.delete_assistant()


@router.get("/assistant/entities")
async def assistant_entities(
    devices: Annotated[HomeDeviceRepository, Depends(get_home_device_repository)],
    settings: Annotated[CoreSettings, Depends(get_settings)],
    transport: Annotated[httpx2.AsyncBaseTransport | None, Depends(get_home_assistant_transport)],
):
    """What Home Assistant has that Venus can control, to tick and import."""
    row = devices.get_assistant()
    if row is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Connect Home Assistant first")
    try:
        token = decrypt_text(row.token_encrypted, settings.secret_key)
        entities = await list_entities(row.url, token, transport)
    except AssistantError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The saved token can't be read. Save it again.",
        ) from exc
    added = {device.ha_entity_id: device.name for device in devices.list_all() if device.ha_entity_id}
    return [{**entity, "added_as": added.get(entity["entity_id"])} for entity in entities]
