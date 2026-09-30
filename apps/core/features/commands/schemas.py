from typing import Annotated

from pydantic import BaseModel, ConfigDict, HttpUrl, StrictBool, StringConstraints

from venus_protocol.schemas.commands import ApplicationId, ProjectName


class ApprovalDecision(BaseModel):
    approved: StrictBool


class ProposeCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    application_id: ApplicationId


class ProposeUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: HttpUrl


class ProposeProjectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_name: ProjectName


class ProposeTextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
    ]
