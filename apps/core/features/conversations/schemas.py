from pydantic import BaseModel, ConfigDict


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archived: bool
