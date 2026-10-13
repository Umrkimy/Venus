import ipaddress
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
    AfterValidator,
    field_validator,
    model_validator,
)


# A Start menu AppID. The Node checks it against the PC's Start menu list.
# Max 512 matches Core's command_records column; raise both together.
ApplicationId = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=512),
]


def check_project_name(value: str) -> str:
    if value in {".", ".."} or "\\" in value or "/" in value:
        raise ValueError("project name must not contain path separators or be '.' or '..'")
    return value


# A folder name inside the Node's projects root, never a path.
# 255 is the longest folder name Windows allows.
ProjectName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    AfterValidator(check_project_name),
]


class NodeCommandBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: UUID
    device_id: str
    expires_at: datetime

    @field_validator("device_id")
    @classmethod
    def device_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("device_id must not be blank")
        return value

    @field_validator("expires_at")
    @classmethod
    def expires_at_must_be_future(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expires_at must include a timezone")
        if value <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")
        return value


class OpenApplicationCommand(NodeCommandBase):
    kind: Literal["open_application"] = "open_application"
    application_id: ApplicationId


class OpenUrlCommand(NodeCommandBase):
    kind: Literal["open_url"] = "open_url"
    # HttpUrl accepts only http and https, so file: or ms-settings: cannot reach os.startfile.
    url: HttpUrl


class OpenProjectCommand(NodeCommandBase):
    kind: Literal["open_project"] = "open_project"
    project_name: ProjectName


def check_lan_address(value: str) -> str:
    # Home devices live on your home network. An internet address here would
    # turn the Node into a tool for reaching other people's machines.
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValueError("address must be an IP address like 192.168.1.20") from exc
    if not address.is_private or address.is_loopback:
        raise ValueError("address must be on your home network")
    return value


LanAddress = Annotated[str, StringConstraints(strip_whitespace=True), AfterValidator(check_lan_address)]
MacAddress = Annotated[str, StringConstraints(pattern=r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
TuyaText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]

# What each kind of home device can do.
HOME_ACTIONS = {
    "light": {"on", "off", "brightness", "color"},
    "plug": {"on", "off"},
    "tv": {"volume_up", "volume_down", "volume_set", "mute", "unmute"},
    "wake": {"wake"},
    # This PC itself: no address needed.
    "pc": {"volume_up", "volume_down", "volume_set", "mute", "unmute", "lock"},
}


class HomeCommand(NodeCommandBase):
    """Lights, plugs, the TV, waking another PC, or this PC's volume and lock."""

    kind: Literal["home"] = "home"
    device: Literal["light", "plug", "tv", "wake", "pc"]
    action: str
    # Brightness or volume, 0-100.
    value: int | None = Field(default=None, ge=0, le=100)
    color: HexColor | None = None
    # Lights, plugs and the TV: where they are on the home network.
    address: LanAddress | None = None
    # Waking a PC: its network card's MAC address.
    mac: MacAddress | None = None
    # Tuya (Smart Life) lights and plugs: id, local key and protocol version.
    tuya_id: TuyaText | None = None
    local_key: TuyaText | None = None
    tuya_version: float = Field(default=3.3, ge=3.1, le=3.5)

    @model_validator(mode="after")
    def fits_the_device(self) -> "HomeCommand":
        if self.action not in HOME_ACTIONS[self.device]:
            raise ValueError(f"a {self.device} can't {self.action}")
        if self.action in ("brightness", "volume_set") and self.value is None:
            raise ValueError(f"{self.action} needs a value")
        if self.action == "color" and self.color is None:
            raise ValueError("color needs a color")
        if self.device in ("light", "plug") and not (self.address and self.tuya_id and self.local_key):
            raise ValueError(f"a {self.device} needs its address, Tuya id and local key")
        if self.device == "tv" and not self.address:
            raise ValueError("the TV needs its address")
        if self.device == "wake" and not self.mac:
            raise ValueError("waking a PC needs its MAC address")
        return self


# extra="forbid" on every model means a payload can match only one of them.
NodeCommand = OpenApplicationCommand | OpenUrlCommand | OpenProjectCommand | HomeCommand
node_command_adapter = TypeAdapter(NodeCommand)


class CommandResult(BaseModel):
    command_id: UUID
    status: Literal["succeeded", "failed", "denied"]
    detail: str | None = None
