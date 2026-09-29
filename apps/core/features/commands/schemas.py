from pydantic import BaseModel, ConfigDict, StrictBool

from venus_protocol.schemas.commands import ApplicationId


class ApprovalDecision(BaseModel):
    approved: StrictBool


class ProposeCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: ApplicationId
