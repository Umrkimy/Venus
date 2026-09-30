from fastapi import APIRouter

from features.chat.router import router as chat_router
from features.health.router import router as health_router
from features.nodes.router import router as nodes_router
from features.commands.router import router as commands_router
from features.auth.router import router as auth_router
from features.settings.router import router as settings_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(nodes_router)
api_router.include_router(commands_router)
api_router.include_router(auth_router)
api_router.include_router(settings_router)