from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str
    model_config = ConfigDict(extra="forbid")


class OwnerResponse(BaseModel):
    username: str