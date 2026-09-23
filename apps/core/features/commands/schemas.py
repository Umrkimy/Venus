from pydantic import BaseModel, StrictBool


class ApprovalDecision(BaseModel):
    approved: StrictBool