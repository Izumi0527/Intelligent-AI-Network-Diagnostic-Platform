from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.services.ai_service import AIService
from app.services.network_service import NetworkService
from app.api.deps import get_ai_service, get_network_service

router = APIRouter()

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    details: Dict[str, Any]

@router.get("", response_model=HealthResponse)
async def health_check(
    ai_service: AIService = Depends(get_ai_service),
    network_service: NetworkService = Depends(get_network_service)
):
    """API健康检查"""
    # 检查各服务状态
    ai_status = "available" if ai_service else "unavailable"
    network_status = "available" if network_service else "unavailable"
    
    # 统计连接数
    connections = await network_service.get_connections()
    connection_count = len(connections.connections)
    
    # 检查AI模型可用性
    models = await ai_service.get_available_models()
    model_count = len(models.models)
    
    return HealthResponse(
        status="healthy",
        details={
            "ai_service": ai_status,
            "network_service": network_status,
            "connection_count": connection_count,
            "model_count": model_count,
            "version": "1.0.0"
        }
    )