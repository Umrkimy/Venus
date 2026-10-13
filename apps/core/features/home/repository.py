from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from features.home.models.home_assistant import HomeAssistantSetting
from features.home.models.home_device import HomeDevice

ASSISTANT_ROW_ID = 1


class DuplicateNameError(Exception):
    pass


class HomeDeviceRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def list_all(self) -> list[HomeDevice]:
        with Session(self.engine) as session:
            return list(session.scalars(select(HomeDevice).order_by(HomeDevice.name)))

    def get(self, device_id: UUID) -> HomeDevice | None:
        with Session(self.engine) as session:
            return session.get(HomeDevice, device_id)

    def add(
        self,
        name: str,
        kind: str,
        now: datetime,
        address: str | None = None,
        mac: str | None = None,
        tuya_id: str | None = None,
        local_key_encrypted: str | None = None,
        tuya_version: float = 3.3,
        ha_entity_id: str | None = None,
    ) -> HomeDevice:
        device = HomeDevice(
            name=name.strip().lower(),
            kind=kind,
            created_at=now,
            address=address,
            mac=mac,
            tuya_id=tuya_id,
            local_key_encrypted=local_key_encrypted,
            tuya_version=tuya_version,
            ha_entity_id=ha_entity_id,
        )
        with Session(self.engine, expire_on_commit=False) as session:
            session.add(device)
            try:
                session.commit()
            except IntegrityError as exc:
                raise DuplicateNameError(device.name) from exc
        return device

    def delete(self, device_id: UUID) -> bool:
        with Session(self.engine) as session:
            device = session.get(HomeDevice, device_id)
            if device is None:
                return False
            session.delete(device)
            session.commit()
            return True

    def get_assistant(self) -> HomeAssistantSetting | None:
        with Session(self.engine) as session:
            return session.get(HomeAssistantSetting, ASSISTANT_ROW_ID)

    def set_assistant(self, url: str, token_encrypted: str | None) -> None:
        """Save the address; a None token keeps the saved one."""
        with Session(self.engine) as session:
            row = session.get(HomeAssistantSetting, ASSISTANT_ROW_ID)
            if row is None:
                if token_encrypted is None:
                    raise ValueError("token needed the first time")
                session.add(HomeAssistantSetting(ASSISTANT_ROW_ID, url, token_encrypted))
            else:
                row.url = url
                if token_encrypted is not None:
                    row.token_encrypted = token_encrypted
            session.commit()

    def delete_assistant(self) -> None:
        """Forget Home Assistant and every device imported from it."""
        with Session(self.engine) as session:
            row = session.get(HomeAssistantSetting, ASSISTANT_ROW_ID)
            if row is not None:
                session.delete(row)
            for device in session.scalars(select(HomeDevice).where(HomeDevice.ha_entity_id.is_not(None))):
                session.delete(device)
            session.commit()
