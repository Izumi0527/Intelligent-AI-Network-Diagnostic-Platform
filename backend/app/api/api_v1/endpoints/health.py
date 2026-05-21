from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.services.ai.manager import AIServiceManager
from app.api.deps import get_ai_service_manager

router = APIRouter()

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    details: Dict[str, Any]

@router.get("", response_model=HealthResponse)
async def health_check(
    ai_manager: AIServiceManager = Depends(get_ai_service_manager),
):
    """API健康检查"""
    # 检查各服务状态
    ai_status = "available" if ai_manager else "unavailable"

    # 检查AI模型可用性
    models = await ai_manager.get_models_response()
    model_count = len(models.models)

    return HealthResponse(
        status="healthy",
        details={
            "ai_service": ai_status,
            "network_service": "deprecated",
            "connection_count": 0,
            "model_count": model_count,
            "version": "1.0.0"
        }
    )
