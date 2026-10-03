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


# Fish Audio's text-to-speech models; the free one is the default.
FishModel = Literal["s2.1-pro-free", "s2.1-pro", "s2-pro", "s1"]


class VoiceSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voice_id: str = Field(max_length=100)
    model: FishModel
    api_key: str | None = Field(default=None, max_length=500)
