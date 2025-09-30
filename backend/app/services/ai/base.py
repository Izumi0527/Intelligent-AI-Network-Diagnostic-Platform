"""
AI服务基类
定义统一的AI模型接口规范
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple
from enum import Enum
import aiohttp

from app.models.ai import AIModel, Message, ChatRequest, ChatResponse, StreamEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProviderType(Enum):
    """AI服务提供商类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic" 
    DEEPSEEK = "deepseek"


class AIProviderBase(ABC):
    """AI服务提供商基类"""
    
    def __init__(self, api_key: str, provider_type: ProviderType):
        self.api_key = api_key
        self.provider_type = provider_type
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
    
    async def initialize(self):
        """初始化HTTP会话"""
        if not self.session:
            # 为连接检查使用更快的超时设置
            timeout = aiohttp.ClientTimeout(total=5, connect=2)
            self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()
            self.session = None
    
    @abstractmethod
    def get_available_models(self) -> List[AIModel]:
        """获取可用模型列表"""
        pass
    
    @abstractmethod
    async def check_connection(self) -> Tuple[bool, str]:
        """检查API连接状态"""
        pass
    
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """非流式对话"""
        pass
    
    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamEvent, None]:
        """流式对话"""
        pass
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.api_key)
    
    def _create_headers(self, additional_headers: Dict[str, str] = None) -> Dict[str, str]:
        """创建请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AI-Network-Platform/1.0"
        }
        
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    def _handle_api_error(self, status: int, response_text: str) -> str:
        """处理API错误"""
        error_messages = {
            400: "请求参数错误",
            401: "API密钥无效或未授权",
            403: "访问被禁止",
            429: "请求频率过高，请稍后重试",
            500: "服务器内部错误",
            503: "服务暂时不可用"
        }
        
        base_message = error_messages.get(status, f"未知错误 (状态码: {status})")
        
        try:
            # 尝试解析错误详情
            import json
            error_data = json.loads(response_text)
            if "error" in error_data:
                error_detail = error_data["error"]
                if isinstance(error_detail, dict) and "message" in error_detail:
                    return f"{base_message}: {error_detail['message']}"
                elif isinstance(error_detail, str):
                    return f"{base_message}: {error_detail}"
        except:
            pass
        
        return base_message