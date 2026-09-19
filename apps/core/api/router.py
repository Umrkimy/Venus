from fastapi import APIRouter

from api.routes.chat import router as chat_router
from api.routes.health import router as health_router
from api.routes.nodes import router as nodes_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(nodes_router)
