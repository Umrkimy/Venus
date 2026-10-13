from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from features.home.models.home_device import HomeDevice


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
