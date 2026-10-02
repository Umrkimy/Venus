from pydantic import BaseModel, ConfigDict, Field, field_validator


class MemoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=300)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value
