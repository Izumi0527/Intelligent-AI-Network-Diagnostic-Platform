from fastapi import APIRouter

from app.api.api_v1.endpoints import ai, network, health, terminal

api_router = APIRouter()

# 添加子路由 - AI
api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
api_router.include_router(network.router, prefix="/network", tags=["Network"])
api_router.include_router(terminal.router, prefix="/terminal", tags=["Terminal"])
api_router.include_router(health.router, prefix="/health", tags=["Health"]) 

