from fastapi import APIRouter

from features.chat.fake_provider import generate_reply
from features.chat.schemas import ChatRequest

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest):
    return {
        "reply": generate_reply(request.message),
        "provider": "fake",
    }
