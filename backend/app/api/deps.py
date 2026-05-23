import secrets
from typing import Any, Optional

from fastapi import Depends, Header, HTTPException, Request, status

from app.config.settings import settings
from app.services.ai.application_service import AIApplicationService
from app.services.ai.manager import AIServiceManager
from app.services.deepseek_service import DeepseekService
from app.services.search.brave_search import BraveSearchClient
from app.services.terminal_service import TerminalService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _get_or_create_state_service(
    request: Request,
    attr_name: str,
    factory: type[Any],
) -> Any:
    """从 app.state 获取服务；缺失时在当前应用实例内懒创建。"""
    if hasattr(request.app.state, attr_name):
        return getattr(request.app.state, attr_name)

    service = factory()
    setattr(request.app.state, attr_name, service)
    return service


def get_deepseek_service(request: Request) -> DeepseekService:
    """获取Deepseek服务实例"""
    return _get_or_create_state_service(
        request,
        "deepseek_service",
        DeepseekService,
    )


def get_ai_service_manager(request: Request) -> AIServiceManager:
    """获取AI服务管理器实例"""
    return _get_or_create_state_service(
        request,
        "ai_service_manager",
        AIServiceManager,
    )


def get_ai_application_service(
    ai_manager: AIServiceManager = Depends(get_ai_service_manager),
) -> AIApplicationService:
    """获取 AI 应用服务实例。"""
    return AIApplicationService(ai_manager)


def get_brave_search_client(request: Request) -> BraveSearchClient:
    """获取 Brave Search 单例 client（按应用实例缓存到 app.state）。"""
    return _get_or_create_state_service(
        request,
        "brave_search_client",
        BraveSearchClient,
    )


def get_terminal_service(request: Request) -> TerminalService:
    """获取终端服务实例"""
    return _get_or_create_state_service(
        request,
        "terminal_service",
        TerminalService,
    )


def _validate_internal_api_token(authorization: Optional[str]) -> None:
    """校验内部 API Token；关闭鉴权时保持兼容。"""
    if not getattr(settings, "API_AUTH_ENABLED", False):
        return

    expected_token = getattr(settings, "INTERNAL_API_TOKEN", None)
    if not expected_token:
        logger.error("已启用 API_AUTH_ENABLED，但 INTERNAL_API_TOKEN 未配置")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="内部 API 鉴权未配置",
        )

    scheme, _, provided_token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not provided_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未授权",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_internal_api_token(
    authorization: Optional[str] = Header(default=None),
) -> None:
    """受保护内部接口统一鉴权依赖。"""
    _validate_internal_api_token(authorization)


async def require_development_internal_api_token(
    authorization: Optional[str] = Header(default=None),
) -> None:
    """调试接口必须同时满足 development 环境与内部鉴权。"""
    if (settings.APP_ENV or "").lower() != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="接口不存在",
        )

    _validate_internal_api_token(authorization)
