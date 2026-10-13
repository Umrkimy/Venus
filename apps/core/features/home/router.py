from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from config import CoreSettings, get_settings
from features.auth.dependencies import require_owner
from features.home.dependencies import get_home_device_repository
from features.home.models.home_device import HomeDevice
from features.home.repository import DuplicateNameError, HomeDeviceRepository
from features.home.schemas import HomeDeviceRequest
from features.settings.router import encrypt_key

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
