"""
AI服务管理器
统一管理所有AI服务提供商和模型
"""

import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple
from datetime import datetime

from app.services.ai.base import AIProviderBase, ProviderType
from app.services.ai.providers.openai_provider import OpenAIProvider
from app.services.ai.providers.claude_provider import ClaudeProvider
from app.services.ai.providers.deepseek_provider import DeepseekProvider
from app.models.ai import (
    AIModel, Message, ChatRequest, ChatResponse,
    ModelConnectionStatus, ModelsResponse, StreamEvent
)
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIServiceManager:
    """AI服务管理器"""
    
    def __init__(self):
        """初始化AI服务管理器"""
        self.providers: Dict[ProviderType, AIProviderBase] = {}
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
    
    def get_available_models(self) -> List[AIModel]:
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
    
    async def get_models_response(self) -> ModelsResponse:
        """获取模型列表响应"""
        logger.info("开始获取模型列表响应")
        models = self.get_available_models()
        logger.info(f"get_models_response: 获取到 {len(models)} 个模型")
        
        # 获取每个提供商的连接状态（使用快速检查或缓存状态）
        connection_status = {}
        for provider_type, provider in self.providers.items():
            try:
                # 使用快速超时的连接检查
                is_connected, message = await asyncio.wait_for(
                    provider.check_connection(), 
                    timeout=3.0  # 3秒超时
                )
                connection_status[provider_type.value] = ModelConnectionStatus(
                    connected=is_connected,
                    message=message,
                    last_check=datetime.now().isoformat()
                )
            except asyncio.TimeoutError:
                connection_status[provider_type.value] = ModelConnectionStatus(
                    connected=False,
                    message="连接检查超时（3秒），状态未知",
                    last_check=datetime.now().isoformat()
                )
            except Exception as e:
                connection_status[provider_type.value] = ModelConnectionStatus(
                    connected=False,
                    message=f"检查失败: {str(e)}",
                    last_check=datetime.now().isoformat()
                )
        
        return ModelsResponse(
            models=models,
            status=connection_status
        )
    
    async def check_model_status(self, model_id: str) -> Tuple[bool, str]:
        """检查特定模型的连接状态"""
        provider = self._get_provider_for_model(model_id)
        if not provider:
            return False, f"未找到模型 {model_id} 的服务提供商"
        
        return await provider.check_connection()
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """非流式对话"""
        provider = self._get_provider_for_model(request.model)
        if not provider:
            return ChatResponse(
                id="error",
                model=request.model,
                message=Message(role="assistant", content=f"不支持的模型: {request.model}"),
                usage={"error": True}
            )
        
        logger.info(f"使用模型 {request.model} 进行非流式对话")
        return await provider.chat(request)
    
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
    
    def get_provider_stats(self) -> Dict[str, Any]:
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


# 全局AI服务管理器实例
ai_service_manager = AIServiceManager()