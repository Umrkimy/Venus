from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CommandModeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["confirm", "full"]


class LlmSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["fake", "openai"]
    model: str = Field(max_length=100)
    api_key: str | None = Field(default=None, max_length=500)
