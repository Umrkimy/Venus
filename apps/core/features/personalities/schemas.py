from pydantic import BaseModel, ConfigDict, Field, field_validator


class PersonalityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=40)
    text: str = Field(max_length=4000)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value


class PersonalityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # All optional: only the fields sent are changed.
    name: str | None = Field(default=None, max_length=40)
    text: str | None = Field(default=None, max_length=4000)
    active: bool | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("name must not be blank")
        return value
