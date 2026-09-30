from typing import Literal

from pydantic import BaseModel, ConfigDict


class CommandModeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["confirm", "full"]