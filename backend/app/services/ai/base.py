"""
AI服务基类
定义统一的AI模型接口规范
"""

import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Optional

import aiohttp

from app.models.ai import AIModel, ChatRequest, StreamEvent
from app.utils.logger import get_logger, redact_sensitive_text

logger = get_logger(__name__)
AI_CLIENT_SAFE_ERROR_MESSAGE = "AI 服务暂时不可用，请稍后重试"
SENSITIVE_CLIENT_ERROR_MARKERS = (
    "authorization",
    "password",
    "passwd",
    "token",
    "api_key",
    "api-key",
    "secret",
    "http://",
    "https://",
    "upstream",
)


def safe_ai_client_message(message: str) -> str:
    """将可能来自上游的错误转换为客户端安全文案。"""
    text = str(message)
    redacted = redact_sensitive_text(text, max_length=1000)
    lower_text = text.lower()
    if redacted != text or any(marker in lower_text for marker in SENSITIVE_CLIENT_ERROR_MARKERS):
        return AI_CLIENT_SAFE_ERROR_MESSAGE
    return text


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
    def get_available_models(self) -> list[AIModel]:
        """获取可用模型列表"""
        pass

    @abstractmethod
    async def check_connection(self) -> tuple[bool, str]:
        """检查API连接状态"""
        pass

    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamEvent, None]:
        """流式对话"""
        pass

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.api_key)

    def _create_headers(self, additional_headers: dict[str, str] = None) -> dict[str, str]:
        """创建请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AI-Network-Platform/1.0"
        }

        if additional_headers:
            headers.update(additional_headers)

        return headers

    def _generation_options(
        self,
        request: ChatRequest,
        default_max_tokens: int,
        default_temperature: float = 0.7,
    ) -> dict[str, int | float]:
        """构造上游生成参数，避免把 None 发送给第三方服务。"""
        options: dict[str, int | float] = {
            "max_tokens": (
                request.max_tokens
                if request.max_tokens is not None
                else default_max_tokens
            ),
            "temperature": (
                request.temperature
                if request.temperature is not None
                else default_temperature
            ),
        }
        if request.top_p is not None:
            options["top_p"] = request.top_p
        return options

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
        except Exception:
            pass

        return base_message

    def _error_stream_event(
        self,
        error_detail: str,
        error_code: str = "upstream_error",
    ) -> StreamEvent:
        """构造面向客户端的安全流式错误事件。"""
        logger.error(
            "%s 流式调用失败: %s",
            self.provider_type.value,
            redact_sensitive_text(error_detail, max_length=300),
        )
        request_id = str(uuid.uuid4())
        return StreamEvent(
            type="error",
            data={
                "error": AI_CLIENT_SAFE_ERROR_MESSAGE,
                "error_code": error_code,
                "provider": self.provider_type.value,
                "request_id": request_id,
            },
        )
