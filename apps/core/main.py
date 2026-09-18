from fastapi import FastAPI

from pydantic import BaseModel


app = FastAPI()

class ChatRequest(BaseModel):
    message: str


@app.get("/health")
async def health_check():
    return {"status":"ok"}

@app.post("/chat")
async def chat(request: ChatRequest):
    return {"reply": f"Fake Venus: {request.message}", "provider": "fake"}