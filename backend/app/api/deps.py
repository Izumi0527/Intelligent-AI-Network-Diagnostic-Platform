import secrets
from typing import Optional

from fastapi import Header, HTTPException, status

from app.services.ai.manager import AIServiceManager, ai_service_manager
from app.services.network_service import NetworkService
from app.services.terminal_service import TerminalService
from app.services.deepseek_service import DeepseekService
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 全局服务实例
_network_service = None
_terminal_service = None
_deepseek_service = None

def get_deepseek_service() -> DeepseekService:
    """获取Deepseek服务实例"""
    global _deepseek_service
    if _deepseek_service is None and settings.DEEPSEEK_API_ENABLED:
        _deepseek_service = DeepseekService()
    elif _deepseek_service is None:
        # 如果服务未启用，仍返回实例但功能受限
        _deepseek_service = DeepseekService()
    return _deepseek_service

def get_ai_service_manager() -> AIServiceManager:
    """获取AI服务管理器实例"""
    return ai_service_manager

def get_network_service() -> NetworkService:
    """获取网络服务实例"""
    global _network_service
    if _network_service is None:
        _network_service = NetworkService()
    return _network_service

def get_terminal_service() -> TerminalService:
    """获取终端服务实例"""
    global _terminal_service
    if _terminal_service is None:
        _terminal_service = TerminalService()
    return _terminal_service


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
