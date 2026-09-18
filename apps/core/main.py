from fastapi import FastAPI

from pydantic import BaseModel, field_validator


app = FastAPI()

class ChatRequest(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


@app.get("/health")
async def health_check():
    return {"status":"ok"}


@app.post("/chat")
async def chat(request: ChatRequest):
    return {"reply": f"Fake Venus: {request.message}", "provider": "fake"}
