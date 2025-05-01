from typing import Generator

from fastapi import Depends

from app.services.ai_service import AIService
from app.services.network_service import NetworkService
from app.services.terminal_service import TerminalService
from app.services.deepseek_service import DeepseekService
from app.config.settings import settings

# 全局服务实例
_ai_service = None
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

def get_ai_service(deepseek_service: DeepseekService = Depends(get_deepseek_service)) -> AIService:
    """获取AI服务实例"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService(deepseek_service=deepseek_service)
    return _ai_service

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