from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=60)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must not be blank")
        return value


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Both optional: only the fields sent are changed.
    name: str | None = Field(default=None, max_length=60)
    archived: bool | None = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("name must not be blank")
        return value
