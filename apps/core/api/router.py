from fastapi import APIRouter

from features.health.router import router as health_router
from features.nodes.router import router as nodes_router
from features.nodes.devices_router import router as devices_router
from features.commands.router import router as commands_router
from features.conversations.router import router as conversations_router
from features.projects.router import router as projects_router
from features.personalities.router import router as personalities_router
from features.memories.router import router as memories_router
from features.auth.router import router as auth_router
from features.settings.router import router as settings_router
from features.shortcuts.router import router as shortcuts_router
from features.voice.router import router as voice_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(nodes_router)
api_router.include_router(devices_router)
api_router.include_router(commands_router)
api_router.include_router(auth_router)
api_router.include_router(settings_router)
api_router.include_router(shortcuts_router)
api_router.include_router(conversations_router)
api_router.include_router(projects_router)
api_router.include_router(personalities_router)
api_router.include_router(memories_router)
api_router.include_router(voice_router)
