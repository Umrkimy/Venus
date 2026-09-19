from pydantic import BaseModel, ConfigDict, field_validator


class NodeHello(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str

    @field_validator("device_id")
    @classmethod
    def device_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("device_id must not be blank")
        return value
