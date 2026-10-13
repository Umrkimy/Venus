from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from venus_protocol.schemas.commands import (
    HOME_ASSISTANT_DOMAINS,
    HomeAssistantEntity,
    HomeAssistantToken,
    HomeAssistantUrl,
    LanAddress,
    MacAddress,
    TuyaText,
)


class HomeDeviceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # What you call it in chat, e.g. "bedroom light".
    name: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9 '-]*$")
    kind: Literal["light", "plug", "tv", "pc", "aircon", "scene"]
    address: LanAddress | None = None
    mac: MacAddress | None = None
    tuya_id: TuyaText | None = None
    local_key: TuyaText | None = None
    tuya_version: float = Field(default=3.3, ge=3.1, le=3.5)
    # From Home Assistant instead: its entity, like light.bedroom.
    ha_entity_id: HomeAssistantEntity | None = None

    @model_validator(mode="after")
    def has_what_the_kind_needs(self) -> "HomeDeviceRequest":
        if self.ha_entity_id is not None:
            if self.ha_entity_id.split(".")[0] not in HOME_ASSISTANT_DOMAINS.get(self.kind, set()):
                raise ValueError(f"{self.ha_entity_id} can't be a {self.kind}")
            return self
        if self.kind in ("aircon", "scene"):
            raise ValueError("Air-con and scenes come from Home Assistant")
        if self.kind in ("light", "plug") and not (self.address and self.tuya_id and self.local_key):
            raise ValueError("Lights and plugs need their IP address, Tuya id and local key")
        if self.kind == "tv" and not self.address:
            raise ValueError("The TV needs its IP address")
        if self.kind == "pc" and not self.mac:
            raise ValueError("A PC to wake needs its MAC address")
        return self


class HomeAssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HomeAssistantUrl
    # Empty keeps the saved token.
    token: HomeAssistantToken | None = None
