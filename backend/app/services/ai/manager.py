"""
AI服务管理器
统一管理所有AI服务提供商和模型
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, Optional

from app.config.settings import settings
from app.models.ai import (
    AIModel,
    ChatRequest,
    ModelConnectionStatus,
    ModelsResponse,
    StreamEvent,
)
from app.services.ai.base import AIProviderBase, ProviderType, safe_ai_client_message
from app.services.ai.providers.claude_provider import ClaudeProvider
from app.services.ai.providers.deepseek_provider import DeepseekProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 单一超时常量：/ai/models 与 /ai/models/{id}/status 两个端点统一使用。
# 8 秒覆盖 Windows 冷启动 DNS+TCP+TLS 首请求场景（实测 2-5 s），同时保留快速失败语义。
# 历史问题：曾仅 get_models_response 使用 3.0 s，而 check_model_status 走 httpx 自身 30 s，
# 冷启动时前者超时、后者成功，导致前端"已连接 + 未配置"矛盾态。
CONNECTION_CHECK_TIMEOUT_SECONDS = 8.0


class AIServiceManager:
    """AI服务管理器"""

    def __init__(self):
        """初始化AI服务管理器"""
        self.providers: dict[ProviderType, AIProviderBase] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """初始化所有可用的服务提供商"""
        # 初始化OpenAI提供商
        if settings.OPENAI_API_KEY:
            self.providers[ProviderType.OPENAI] = OpenAIProvider(settings.OPENAI_API_KEY)
            logger.info("已加载OpenAI服务提供商")

        # 初始化Claude提供商
        if settings.ANTHROPIC_API_KEY:
            self.providers[ProviderType.ANTHROPIC] = ClaudeProvider(settings.ANTHROPIC_API_KEY)
            logger.info("已加载Claude服务提供商")

        # 初始化Deepseek提供商
        if settings.DEEPSEEK_API_KEY:
            self.providers[ProviderType.DEEPSEEK] = DeepseekProvider(settings.DEEPSEEK_API_KEY)
            logger.info("已加载Deepseek服务提供商")

        logger.info(f"AI服务管理器初始化完成，共加载 {len(self.providers)} 个服务提供商")

    def get_available_models(self) -> list[AIModel]:
        """获取所有可用模型"""
        models = []
        for provider_type, provider in self.providers.items():
            provider_models = provider.get_available_models()
            logger.info(f"从 {provider_type.value} 提供商获取到 {len(provider_models)} 个模型")

            # 添加调试信息，显示具体的模型
            if provider_models:
                model_names = [model.value for model in provider_models]
                logger.info(f"{provider_type.value} 提供商的模型: {model_names}")
            else:
                logger.warning(f"{provider_type.value} 提供商返回了空的模型列表，is_available(): {provider.is_available()}")

            models.extend(provider_models)

        logger.info(f"总共获取到 {len(models)} 个可用模型")
        return models

    async def _check_connection_with_timeout(
        self,
        provider: AIProviderBase,
        timeout: float = CONNECTION_CHECK_TIMEOUT_SECONDS,
    ) -> tuple[bool, str]:
        """统一封装的"带超时连接检查"：两个端点共用同一超时阈值，
        避免冷启动时不同端点对同一 provider 给出矛盾结论。"""
        try:
            return await asyncio.wait_for(provider.check_connection(), timeout=timeout)
        except asyncio.TimeoutError:
            return False, f"连接检查超时（{timeout:.0f}秒），状态未知"
        except Exception as e:
            return False, safe_ai_client_message(f"检查失败: {str(e)}")

    async def get_models_response(self) -> ModelsResponse:
        """获取模型列表响应"""
        logger.info("开始获取模型列表响应")
        models = self.get_available_models()
        logger.info(f"get_models_response: 获取到 {len(models)} 个模型")

        # 获取每个提供商的连接状态（使用统一超时的连接检查）
        connection_status = {}
        for provider_type, provider in self.providers.items():
            is_connected, message = await self._check_connection_with_timeout(provider)
            connection_status[provider_type.value] = ModelConnectionStatus(
                connected=is_connected,
                message=message if is_connected else safe_ai_client_message(message),
                last_check=datetime.now().isoformat()
            )

        return ModelsResponse(
            models=models,
            status=connection_status
        )

    async def check_model_status(self, model_id: str) -> tuple[bool, str]:
        """检查特定模型的连接状态"""
        provider = self._get_provider_for_model(model_id)
        if not provider:
            return False, f"未找到模型 {model_id} 的服务提供商"

        # 与 get_models_response 共用同一超时阈值，保证两个端点判定一致
        return await self._check_connection_with_timeout(provider)

    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamEvent, None]:
        """流式对话"""
        provider = self._get_provider_for_model(request.model)
        if not provider:
            yield StreamEvent(
                type="error",
                data={"error": f"不支持的模型: {request.model}"}
            )
            return

        logger.info(f"使用模型 {request.model} 进行流式对话")
        async for event in provider.chat_stream(request):
            yield event

    def _get_provider_for_model(self, model_id: str) -> Optional[AIProviderBase]:
        """根据模型ID获取对应的服务提供商"""
        # OpenAI模型
        if model_id.startswith('gpt-'):
            return self.providers.get(ProviderType.OPENAI)

        # Claude模型
        elif model_id.startswith('claude-'):
            return self.providers.get(ProviderType.ANTHROPIC)

        # Deepseek模型
        elif model_id.startswith('deepseek-'):
            return self.providers.get(ProviderType.DEEPSEEK)

        # 尝试从所有提供商中找到匹配的模型
        for provider in self.providers.values():
            models = provider.get_available_models()
            for model in models:
                if model.value == model_id:  # 使用value字段进行匹配
                    return provider

        return None

    def is_model_available(self, model_id: str) -> bool:
        """检查模型是否可用"""
        return self._get_provider_for_model(model_id) is not None

    def get_provider_stats(self) -> dict[str, Any]:
        """获取服务提供商统计信息"""
        stats = {
            "total_providers": len(self.providers),
            "providers": {}
        }

        for provider_type, provider in self.providers.items():
            models = provider.get_available_models()
            stats["providers"][provider_type.value] = {
                "available": provider.is_available(),
                "model_count": len(models),
                "models": [model.id for model in models]
            }

        return stats

    async def cleanup(self):
        """清理所有服务提供商资源"""
        logger.info("正在清理AI服务管理器资源...")

        cleanup_tasks = []
        for provider in self.providers.values():
            cleanup_tasks.append(provider.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        logger.info("AI服务管理器资源清理完成")
