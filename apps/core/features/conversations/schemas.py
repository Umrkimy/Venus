from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Both optional: only the fields sent are changed.
    archived: bool | None = None
    # null takes the chat out of its project.
    project_id: UUID | None = None
