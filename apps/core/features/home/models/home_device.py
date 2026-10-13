from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from storage.base import Base


class HomeDevice(Base):
    """A light, plug, TV, air-con, scene or PC Venus can control, as the owner added it in Settings, Home."""

    __tablename__ = "home_devices"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    # What you call it in chat: "bedroom light". Saved lowercase, unique.
    name: Mapped[str] = mapped_column(String(40), unique=True)
    # light, plug, tv, pc (a PC to wake), or from Home Assistant also aircon and scene.
    kind: Mapped[str] = mapped_column(String(10))
    # Home network IP (lights, plugs, TV).
    address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    # Network card address (a PC to wake).
    mac: Mapped[str | None] = mapped_column(String(17), nullable=True)
    tuya_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Encrypted like the API keys; never sent back to the page.
    local_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    tuya_version: Mapped[float] = mapped_column(Float, default=3.3)
    # Imported from Home Assistant: its entity, like light.bedroom.
    ha_entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(
        self,
        name: str,
        kind: str,
        created_at: datetime,
        address: str | None = None,
        mac: str | None = None,
        tuya_id: str | None = None,
        local_key_encrypted: str | None = None,
        tuya_version: float = 3.3,
        ha_entity_id: str | None = None,
    ) -> None:
        self.id = uuid4()
        self.name = name
        self.kind = kind
        self.address = address
        self.mac = mac
        self.tuya_id = tuya_id
        self.local_key_encrypted = local_key_encrypted
        self.tuya_version = tuya_version
        self.ha_entity_id = ha_entity_id
        self.created_at = created_at
