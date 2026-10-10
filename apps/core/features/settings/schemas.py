from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class TimeSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time_zone: str = Field(min_length=1, max_length=64)
    country: str = Field(default="", max_length=60)

    @field_validator("time_zone")
    @classmethod
    def known_time_zone(cls, value: str) -> str:
        # Only names Python's time zone list knows, so Core can always use it.
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown time zone") from None
        return value


class ListeningSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # 0.5 to 3 s in quarter seconds, the steps of the web's slider.
    end_pause_ms: int = Field(ge=500, le=3000, multiple_of=250)
