from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=1024)
    model_config = ConfigDict(extra="forbid")


class OwnerResponse(BaseModel):
    username: str