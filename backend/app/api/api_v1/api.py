from fastapi import APIRouter, Depends

from app.api.api_v1.endpoints import ai, network, health, terminal
from app.api.deps import require_internal_api_token

api_router = APIRouter()

# 添加子路由 - AI。AI 能力会消耗外部模型额度，默认按内部接口保护。
api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI"],
    dependencies=[Depends(require_internal_api_token)],
)
api_router.include_router(
    network.router,
    prefix="/network",
    tags=["Network"],
    dependencies=[Depends(require_internal_api_token)],
)
api_router.include_router(
    terminal.router,
    prefix="/terminal",
    tags=["Terminal"],
    dependencies=[Depends(require_internal_api_token)],
)
api_router.include_router(health.router, prefix="/health", tags=["Health"]) 
