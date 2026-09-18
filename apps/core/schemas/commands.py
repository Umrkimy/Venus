from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


class OpenApplicationCommand(BaseModel):
    command_id: UUID
    device_id: str
    application_id: Literal["spotify"]
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def expires_at_must_be_future(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expires_at must include a timezone")

        if value <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")

        return value