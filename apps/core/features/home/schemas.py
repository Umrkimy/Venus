from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from venus_protocol.schemas.commands import LanAddress, MacAddress, TuyaText


class HomeDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # What you call it in chat, e.g. "bedroom light".
    name: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9 '-]*$")
    kind: Literal["light", "plug", "tv", "pc"]
    address: LanAddress | None = None
    mac: MacAddress | None = None
    tuya_id: TuyaText | None = None
    local_key: TuyaText | None = None
    tuya_version: float = Field(default=3.3, ge=3.1, le=3.5)

    @model_validator(mode="after")
    def has_what_the_kind_needs(self) -> "HomeDeviceRequest":
        if self.kind in ("light", "plug") and not (self.address and self.tuya_id and self.local_key):
            raise ValueError("Lights and plugs need their IP address, Tuya id and local key")
        if self.kind == "tv" and not self.address:
            raise ValueError("The TV needs its IP address")
        if self.kind == "pc" and not self.mac:
            raise ValueError("A PC to wake needs its MAC address")
        return self
