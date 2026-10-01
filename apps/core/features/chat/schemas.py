from pydantic import BaseModel, ConfigDict, field_validator


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value
