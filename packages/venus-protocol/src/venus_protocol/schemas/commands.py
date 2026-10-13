import ipaddress
from urllib.parse import urlsplit
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

# Names that only mean something inside a home network.
HOME_SUFFIXES = (".local", ".lan", ".home", ".internal", ".home.arpa")


def check_home_assistant_url(value: str) -> str:
    """http(s)://<home address>[:port], nothing else: the Node sends your token there."""
    parts = urlsplit(value.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("Home Assistant address must look like http://192.168.1.50:8123")
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise ValueError("Home Assistant address is only the start, like http://192.168.1.50:8123")
    host = parts.hostname
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # homeassistant.local, or a one-word name your router knows.
        if "." in host and not host.endswith(HOME_SUFFIXES):
            raise ValueError("Home Assistant address must be on your home network") from None
    else:
        # Loopback is fine: Home Assistant can run on this same PC.
        if not (address.is_private or address.is_loopback):
            raise ValueError("Home Assistant address must be on your home network")
    try:
        parts.port
    except ValueError as exc:
        raise ValueError("Home Assistant port must be a number") from exc
    return f"{parts.scheme}://{parts.netloc}"


HomeAssistantUrl = Annotated[str, StringConstraints(max_length=200), AfterValidator(check_home_assistant_url)]
HomeAssistantToken = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1024, pattern=r"^\S+$")]
HomeAssistantEntity = Annotated[
    str,
    StringConstraints(
        max_length=255,
        pattern=r"^(light|switch|fan|input_boolean|media_player|climate|scene|script)\.[a-z0-9_]+$",
    ),
]
# Which Home Assistant entity types each kind of device can be.
HOME_ASSISTANT_DOMAINS = {
    "light": {"light"},
    "plug": {"switch", "fan", "input_boolean"},
    "tv": {"media_player"},
    "aircon": {"climate"},
    "scene": {"scene", "script"},
}
HvacMode = Literal["cool", "heat", "fan_only", "dry", "auto"]

# What each kind of home device can do.
HOME_ACTIONS = {
    "light": {"on", "off", "brightness", "color"},
    "plug": {"on", "off"},
    # on/off only through Home Assistant (Cast can't power a TV on).
    "tv": {"on", "off", "volume_up", "volume_down", "volume_set", "mute", "unmute"},
    # Air-con and scenes only come from Home Assistant.
    "aircon": {"on", "off", "temperature", "mode"},
    "scene": {"activate"},
    "wake": {"wake"},
    # This PC itself: no address needed.
    "pc": {"volume_up", "volume_down", "volume_set", "mute", "unmute", "lock"},
}


class HomeCommand(NodeCommandBase):
    """Lights, plugs, the TV, air-con, scenes, waking another PC, or this PC's volume and lock."""

    kind: Literal["home"] = "home"
    device: Literal["light", "plug", "tv", "aircon", "scene", "wake", "pc"]
    action: str
    # Brightness or volume 0-100, or the air-con's temperature in °C.
    value: int | None = Field(default=None, ge=0, le=100)
    color: HexColor | None = None
    # Air-con mode for action "mode".
    mode: HvacMode | None = None
    # Lights, plugs and the TV: where they are on the home network.
    address: LanAddress | None = None
    # Waking a PC: its network card's MAC address.
    mac: MacAddress | None = None
    # Tuya (Smart Life) lights and plugs: id, local key and protocol version.
    tuya_id: TuyaText | None = None
    local_key: TuyaText | None = None
    tuya_version: float = Field(default=3.3, ge=3.1, le=3.5)
    # Devices from Home Assistant: where it is, its token and the entity.
    ha_url: HomeAssistantUrl | None = None
    ha_token: HomeAssistantToken | None = None
    ha_entity_id: HomeAssistantEntity | None = None

    @model_validator(mode="after")
    def fits_the_device(self) -> "HomeCommand":
        if self.action not in HOME_ACTIONS[self.device]:
            raise ValueError(f"a {self.device} can't {self.action}")
        if self.action in ("brightness", "volume_set", "temperature") and self.value is None:
            raise ValueError(f"{self.action} needs a value")
        if self.action == "color" and self.color is None:
            raise ValueError("color needs a color")
        if self.action == "temperature" and not 10 <= self.value <= 35:
            raise ValueError("temperature must be 10-35 °C")
        if self.action == "mode" and self.mode is None:
            raise ValueError("mode needs a mode")
        if self.ha_entity_id is not None:
            if not (self.ha_url and self.ha_token):
                raise ValueError("a Home Assistant device needs the address and token")
            if self.ha_entity_id.split(".")[0] not in HOME_ASSISTANT_DOMAINS.get(self.device, set()):
                raise ValueError(f"{self.ha_entity_id} isn't a {self.device}")
            return self
        if self.device in ("aircon", "scene"):
            raise ValueError(f"a {self.device} comes from Home Assistant")
        if self.device == "tv" and self.action in ("on", "off"):
            raise ValueError("turning the TV on or off needs Home Assistant")
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
