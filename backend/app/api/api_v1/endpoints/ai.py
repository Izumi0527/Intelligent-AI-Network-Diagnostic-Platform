from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import (
    get_ai_application_service,
    get_deepseek_service,
    require_development_internal_api_token,
    require_internal_api_token,
)
from app.models.ai import (
    ChatRequest,
    ModelConnectionStatus,
    ModelsResponse,
)
from app.services.ai.application_service import (
    AIApplicationError,
    AIApplicationService,
    AIValidationError,
)
from app.services.deepseek_service import DeepseekService

router = APIRouter()


def _ai_error_response(error: AIApplicationError):
    """将 AI 应用服务异常转换为 HTTP 响应。"""
    if isinstance(error, AIValidationError):
        raise HTTPException(
            status_code=error.status_code,
            detail={
                "code": "validation_error",
                "message": "请求参数验证失败",
                "details": error.detail,
            },
        ) from error

    raise HTTPException(
        status_code=error.status_code,
        detail={
            "code": "upstream_error"
            if error.status_code in {500, 502, 503}
            else "ai_service_error",
            "message": error.client_message,
        },
    ) from error


@router.get("/models", response_model=ModelsResponse)
async def get_models(
    ai_service: AIApplicationService = Depends(get_ai_application_service),
):
    """获取可用的AI模型列表"""
    return await ai_service.get_models_response()


@router.get("/models/{model_id}/status", response_model=ModelConnectionStatus)
async def check_model_status(
    model_id: str,
    ai_service: AIApplicationService = Depends(get_ai_application_service),
):
    """检查模型连接状态"""
    return await ai_service.check_model_status(model_id)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    ai_service: AIApplicationService = Depends(get_ai_application_service),
):
    """AI 聊天 API（SSE 流式响应，唯一对外对话入口）"""
    try:
        result = ai_service.chat_stream(request)
        return StreamingResponse(result.chunks, media_type="text/event-stream")
    except AIApplicationError as error:
        return _ai_error_response(error)


@router.post("/debug/request-format")
async def debug_request_format(
    raw_request: dict[str, Any] = Body(...),
    ai_service: AIApplicationService = Depends(get_ai_application_service),
    _auth: None = Depends(require_development_internal_api_token),
):
    """调试API - 回显请求格式，帮助排查格式问题"""
    return ai_service.debug_request_format(raw_request)


@router.get("/deepseek/status")
async def check_deepseek_connection(
    ai_service: AIApplicationService = Depends(get_ai_application_service),
):
    """检查Deepseek API连接状态"""
    return await ai_service.check_deepseek_connection()


@router.post("/deepseek/analyze-network-log")
async def analyze_network_log(
    log_content: str = Body(..., description="网络日志内容", embed=True),
    query: str = Body(..., description="用户查询", embed=True),
    model: str = Body(
        "deepseek-v4-pro",
        description="使用的模型名称，可选: deepseek-v4-pro 或 deepseek-v4-flash",
    ),
    deepseek_service: DeepseekService = Depends(get_deepseek_service),
    _auth: None = Depends(require_internal_api_token),
):
    """使用Deepseek分析网络日志"""
    return StreamingResponse(
        deepseek_service.analyze_network_log(log_content, query, model),
        media_type="text/event-stream",
    )
