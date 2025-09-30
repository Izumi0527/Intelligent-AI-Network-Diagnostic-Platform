"""
Deepseek服务 - 兼容性适配器
保持原有接口兼容性，内部使用重构后的Deepseek客户端
"""

from typing import Dict, List, Any, Optional, AsyncGenerator, Union, Iterator
from datetime import datetime

from app.services.ai.deepseek import get_deepseek_client
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DeepseekService:
    """Deepseek服务兼容性包装类"""
    
    def __init__(self):
        """初始化Deepseek服务 - 兼容原接口"""
        self.client = get_deepseek_client()  # 使用懒加载函数
        
        # 保持原有属性以兼容现有代码
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com/v1')
        self.model_version = getattr(settings, 'DEEPSEEK_MODEL_VERSION', 'deepseek-chat')
        self.timeout = getattr(settings, 'DEEPSEEK_TIMEOUT', 30)
        self.max_tokens = getattr(settings, 'DEEPSEEK_MAX_TOKENS', 4096)
        self.enabled = getattr(settings, 'DEEPSEEK_API_ENABLED', True)
        self.available_models = ["deepseek-reasoner", "deepseek-chat"]
        
        logger.info(f"Deepseek服务初始化完成（重构版）: API URL={self.api_url}, 启用状态={self.enabled}")
    
    async def check_connection(self) -> bool:
        """检查连接状态 - 兼容原接口"""
        return await self.client.check_connection()
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型 - 兼容原接口"""
        models = self.client.get_available_models()
        # 确保返回的是AIModel对象的字典格式
        result = []
        for model in models:
            if hasattr(model, 'dict'):
                result.append(model.dict())
            elif hasattr(model, '__dict__'):
                # 如果是AIModel对象但没有dict方法，手动转换
                result.append({
                    'value': getattr(model, 'value', ''),
                    'label': getattr(model, 'label', ''),
                    'description': getattr(model, 'description', ''),
                    'features': getattr(model, 'features', []),
                    'max_tokens': getattr(model, 'max_tokens', 4096)
                })
            else:
                result.append(model)
        return result
    
    async def generate_response(self, messages: List[Dict[str, str]], 
                              model: str = "deepseek-chat",
                              stream: bool = False,
                              **kwargs) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """生成响应 - 兼容原接口"""
        return await self.client.generate_response(messages, model, stream, **kwargs)
    
    async def generate_response_stream(self, messages: List[Dict[str, str]],
                                     model: str = "deepseek-chat",
                                     **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """流式响应生成 - 兼容原接口"""
        async for chunk in self.client.generate_response_stream(messages, model, **kwargs):
            yield chunk
    
    async def analyze_network_log(self, log_content: str,
                                query: Optional[str] = None,
                                model: str = "deepseek-chat") -> AsyncGenerator[Dict[str, Any], None]:
        """分析网络日志 - 兼容原接口，支持流式响应"""
        # 如果有query参数，使用它作为分析类型；否则使用默认的error_analysis
        analysis_type = query if query else "error_analysis"

        # 使用流式分析，这更适合网络日志分析的场景
        async for event in self.client.analyze_log_stream(log_content, analysis_type):
            yield event
    
    async def analyze_log_stream(self, log_content: str,
                               analysis_type: str = "error_analysis") -> AsyncGenerator[Dict[str, Any], None]:
        """流式分析网络日志 - 兼容原接口"""
        async for event in self.client.analyze_log_stream(log_content, analysis_type):
            yield event
    
    def classify_log_type(self, log_content: str) -> str:
        """分类日志类型 - 兼容原接口"""
        return self.client.classify_log_type(log_content)
    
    def extract_log_patterns(self, log_content: str) -> Dict[str, List[str]]:
        """提取日志模式 - 兼容原接口"""
        return self.client.extract_log_patterns(log_content)
    
    async def get_status(self) -> Dict[str, Any]:
        """获取服务状态 - 兼容原接口"""
        return await self.client.get_status()
    
    def is_enabled(self) -> bool:
        """检查服务是否启用 - 兼容原接口"""
        return self.client.is_available()
    
    # 以下是原接口中可能存在的其他方法的兼容性实现
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查 - 扩展接口"""
        status = await self.get_status()
        return {
            "healthy": status.get("connected", False),
            "status": "ok" if status.get("connected", False) else "error",
            "details": status
        }
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息 - 扩展接口"""
        models = self.get_available_models()
        for model in models:
            if model.get("id") == model_id:
                return model
        return None
    
    async def test_model(self, model_id: str = "deepseek-chat") -> Dict[str, Any]:
        """测试模型 - 扩展接口"""
        try:
            test_messages = [{"role": "user", "content": "Hello"}]
            response = await self.generate_response(test_messages, model_id)
            
            return {
                "success": not "error" in response,
                "model": model_id,
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "model": model_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup(self):
        """清理资源 - 兼容原接口"""
        await self.client.cleanup()
    
    def __del__(self):
        """析构函数"""
        try:
            import asyncio
            if hasattr(self, 'client') and self.client:
                # 尝试清理，但不强制等待
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.create_task(self.cleanup())
        except:
            pass


# 保持原有的全局实例导出以确保兼容性
deepseek_service = DeepseekService()