import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from venus_protocol.schemas.commands import HomeCommand

from features.home.models.home_assistant import HomeAssistantSetting
from features.home.models.home_device import HomeDevice
from features.home.rules import HomeIntent, HomeTextError
from features.settings.secrets import decrypt_text

# Fields that must never go back to the browser or into the command records.
SECRET_FIELDS = ("local_key", "ha_token")


def without_secrets(command_json: dict) -> dict:
    return {name: value for name, value in command_json.items() if name not in SECRET_FIELDS}


def home_command(
    intent: HomeIntent,
    device: HomeDevice | None,
    node_id: str,
    secret_key: str,
    command_id: UUID | None = None,
    expires_at: datetime | None = None,
    assistant: HomeAssistantSetting | None = None,
) -> HomeCommand:
    """The command the Node runs, with the device's address and (decrypted) Tuya key or Home Assistant token."""
    fields: dict = {}
    if device is not None and device.ha_entity_id:
        if assistant is None or not secret_key:
            raise HomeTextError("Home Assistant isn't connected. Connect it again in Settings, Home.")
        fields = {
            "ha_url": assistant.url,
            "ha_token": decrypt_text(assistant.token_encrypted, secret_key),
            "ha_entity_id": device.ha_entity_id,
        }
    elif device is not None:
        fields = {"address": device.address, "mac": device.mac}
        if device.kind in ("light", "plug"):
            if not secret_key or device.local_key_encrypted is None:
                raise HomeTextError("This light's key can't be read. Add it again in Settings, Home.")
            fields |= {
                "tuya_id": device.tuya_id,
                "local_key": decrypt_text(device.local_key_encrypted, secret_key),
                "tuya_version": device.tuya_version,
            }
    return HomeCommand(
        command_id=command_id or uuid4(),
        device_id=node_id,
        expires_at=expires_at or datetime.now(timezone.utc) + timedelta(minutes=5),
        device=intent.device,
        action=intent.action,
        value=intent.value,
        color=intent.color,
        mode=intent.mode,
        **{name: value for name, value in fields.items() if value is not None},
    )


def intent_payload(intent: HomeIntent) -> str:
    """What the command record keeps until you approve: no address, no key."""
    return json.dumps({
        "device": intent.device,
        "action": intent.action,
        "label": intent.label,
        "home_device_id": str(intent.home_device_id) if intent.home_device_id else None,
        "value": intent.value,
        "color": intent.color,
        "mode": intent.mode,
    })


def intent_from_payload(payload: str) -> HomeIntent:
    data = json.loads(payload)
    device_id = data.get("home_device_id")
    return HomeIntent(
        device=data["device"],
        action=data["action"],
        label=data["label"],
        home_device_id=UUID(device_id) if device_id else None,
        value=data.get("value"),
        color=data.get("color"),
        mode=data.get("mode"),
    )
