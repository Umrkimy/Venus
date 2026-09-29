from pydantic import BaseModel, ConfigDict, Field, field_validator

from venus_protocol.schemas.commands import ApplicationId


class NodeApp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    app_id: ApplicationId


class NodeHello(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str
    # Apps this PC can open; empty if the Node sends none
    apps: list[NodeApp] = Field(default_factory=list)

    @field_validator("device_id")
    @classmethod
    def device_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("device_id must not be blank")
        return value