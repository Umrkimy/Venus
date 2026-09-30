from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
    AfterValidator,
    field_validator,
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


# extra="forbid" on every model means a payload can match only one of them.
NodeCommand = OpenApplicationCommand | OpenUrlCommand | OpenProjectCommand
node_command_adapter = TypeAdapter(NodeCommand)


class CommandResult(BaseModel):
    command_id: UUID
    status: Literal["succeeded", "failed", "denied"]
    detail: str | None = None
