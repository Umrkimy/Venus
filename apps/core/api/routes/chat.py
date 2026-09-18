from fastapi import APIRouter

from providers.fake import generate_reply
from schemas.chat import ChatRequest

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    return {
        "reply": generate_reply(request.message),
        "provider": "fake",
    }