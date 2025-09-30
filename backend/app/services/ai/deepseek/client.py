"""
Deepseek客户端包装器
统一管理Deepseek API访问和专有功能
"""

import httpx
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from datetime import datetime

from app.services.ai.providers.deepseek_provider import DeepseekProvider
from app.services.ai.deepseek.analyzer import NetworkLogAnalyzer
from app.config.settings import settings
from app.models.ai import AIModel, Message, ChatRequest, ChatResponse, StreamEvent
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DeepseekClient:
    """Deepseek客户端包装器"""

    def __init__(self, provider=None):
        self.api_key = settings.DEEPSEEK_API_KEY
        self.enabled = getattr(settings, 'DEEPSEEK_API_ENABLED', True)

        # 初始化组件 - 优先使用注入的provider以避免重复创建
        self.provider = provider
        self.analyzer = None

        if self.api_key and self.enabled:
            # 只有在没有注入provider时才创建新的
            if not self.provider:
                self.provider = DeepseekProvider(self.api_key)
                logger.info("Deepseek客户端创建新的Provider实例")
            else:
                logger.info("Deepseek客户端复用已有Provider实例")

            self.analyzer = NetworkLogAnalyzer(self.api_key)
            logger.info("Deepseek客户端初始化完成")
        else:
            logger.warning("Deepseek客户端未启用或缺少API密钥")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.api_key and self.enabled and self.provider)
    
    def get_available_models(self) -> List[AIModel]:
        """获取可用模型列表"""
        if not self.is_available():
            return []
        return self.provider.get_available_models()
    
    async def check_connection(self) -> bool:
        """检查连接状态"""
        if not self.is_available():
            return False
        
        try:
            success, _ = await self.provider.check_connection()
            return success
        except Exception as e:
            logger.error(f"Deepseek连接检查失败: {str(e)}")
            return False
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              model: str = "deepseek-chat", 
                              stream: bool = False, 
                              **kwargs) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """生成响应（兼容原接口）"""
        if not self.is_available():
            if stream:
                async def error_generator():
                    yield {"error": "Deepseek服务不可用"}
                return error_generator()
            else:
                return {"error": "Deepseek服务不可用"}
        
        try:
            # 转换为ChatRequest格式
            message_objects = [Message(role=msg["role"], content=msg["content"]) for msg in messages]
            request = ChatRequest(
                model=model,
                messages=message_objects,
                **kwargs
            )
            
            if stream:
                return self._stream_response_generator(request)
            else:
                response = await self.provider.chat(request)
                return {
                    "id": response.id,
                    "content": response.message.content,
                    "model": response.model,
                    "usage": response.usage
                }
                
        except Exception as e:
            logger.error(f"Deepseek响应生成失败: {str(e)}")
            if stream:
                async def error_generator():
                    yield {"error": str(e)}
                return error_generator()
            else:
                return {"error": str(e)}
    
    async def _stream_response_generator(self, request: ChatRequest) -> AsyncGenerator[Dict[str, Any], None]:
        """流式响应生成器"""
        try:
            async for event in self.provider.chat_stream(request):
                if event.type == "content":
                    yield {"content": event.data.get("content", "")}
                elif event.type == "done":
                    yield {"done": True}
                elif event.type == "error":
                    yield {"error": event.data.get("error", "未知错误")}
        except Exception as e:
            yield {"error": str(e)}
    
    async def generate_response_stream(self, messages: List[Dict[str, str]], 
                                     model: str = "deepseek-chat",
                                     **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """流式响应生成（兼容原接口）"""
        async for chunk in await self.generate_response(messages, model, stream=True, **kwargs):
            yield chunk
    
    async def analyze_network_log(self, log_content: str, 
                                analysis_type: str = "error_analysis") -> Dict[str, Any]:
        """分析网络日志"""
        if not self.analyzer:
            return {
                "success": False,
                "error": "网络日志分析器不可用",
                "timestamp": datetime.now().isoformat()
            }
        
        return await self.analyzer.analyze_network_log(log_content, analysis_type)
    
    async def analyze_log_stream(self, log_content: str,
                               analysis_type: str = "error_analysis") -> AsyncGenerator[Dict[str, Any], None]:
        """流式分析网络日志"""
        if not self.analyzer:
            yield {
                "type": "error",
                "data": {"error": "网络日志分析器不可用"}
            }
            return
        
        async for event in self.analyzer.analyze_log_stream(log_content, analysis_type):
            yield event
    
    def classify_log_type(self, log_content: str) -> str:
        """分类日志类型"""
        if not self.analyzer:
            return "error_analysis"
        return self.analyzer.classify_log_type(log_content)
    
    def extract_log_patterns(self, log_content: str) -> Dict[str, List[str]]:
        """提取日志模式"""
        if not self.analyzer:
            return {}
        return self.analyzer.extract_log_patterns(log_content)
    
    async def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = {
            "enabled": self.enabled,
            "api_key_configured": bool(self.api_key),
            "provider_available": bool(self.provider),
            "analyzer_available": bool(self.analyzer),
            "connected": False,
            "models": [],
            "timestamp": datetime.now().isoformat()
        }
        
        if self.is_available():
            try:
                status["connected"] = await self.check_connection()
                status["models"] = [model.dict() for model in self.get_available_models()]
            except Exception as e:
                logger.error(f"获取Deepseek状态失败: {str(e)}")
                status["error"] = str(e)
        
        return status
    
    async def cleanup(self):
        """清理资源"""
        cleanup_tasks = []
        
        if self.provider:
            cleanup_tasks.append(self.provider.cleanup())
        
        if self.analyzer:
            cleanup_tasks.append(self.analyzer.cleanup())
        
        if cleanup_tasks:
            import asyncio
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        logger.info("Deepseek客户端资源清理完成")


# 延迟初始化的全局Deepseek客户端实例
deepseek_client = None

def get_deepseek_client():
    """获取全局Deepseek客户端实例，支持依赖注入"""
    global deepseek_client

    if deepseek_client is None:
        # 尝试从AI服务管理器获取已存在的DeepseekProvider
        try:
            from app.services.ai.manager import ai_service_manager
            from app.services.ai.base import ProviderType

            existing_provider = ai_service_manager.providers.get(ProviderType.DEEPSEEK)
            if existing_provider:
                logger.info("从AI服务管理器获取已有的Deepseek Provider")
                deepseek_client = DeepseekClient(provider=existing_provider)
            else:
                logger.info("AI服务管理器中无Deepseek Provider，创建独立客户端")
                deepseek_client = DeepseekClient()

        except ImportError:
            logger.info("AI服务管理器不可用，创建独立Deepseek客户端")
            deepseek_client = DeepseekClient()

    return deepseek_client