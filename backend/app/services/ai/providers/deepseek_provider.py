"""
Deepseek服务提供商实现
处理与Deepseek API的交互
"""

import json
import uuid
from typing import List, Dict, Any, AsyncGenerator, Tuple
import httpx

from app.services.ai.base import AIProviderBase, ProviderType
from app.models.ai import AIModel, Message, ChatRequest, ChatResponse, StreamEvent
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DeepseekProvider(AIProviderBase):
    """Deepseek服务提供商"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, ProviderType.DEEPSEEK)
        self.base_url = getattr(settings, 'DEEPSEEK_API_URL', 'https://api.deepseek.com/v1')
        self.timeout = getattr(settings, 'DEEPSEEK_TIMEOUT', 30)
        self.max_tokens = getattr(settings, 'DEEPSEEK_MAX_TOKENS', 4096)

        # 从配置动态加载模型
        from app.utils.model_config import ModelConfigParser
        self.models = ModelConfigParser.parse_deepseek_models()
        logger.info(f"Deepseek Provider加载了 {len(self.models)} 个模型")

        self.client = None
    
    async def initialize(self):
        """初始化HTTP客户端"""
        if not self.client:
            self.client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
    
    async def cleanup(self):
        """清理资源"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    def get_available_models(self) -> List[AIModel]:
        """获取可用模型列表"""
        # 添加调试信息
        from app.utils.logger import get_logger
        debug_logger = get_logger(__name__)
        debug_logger.info(f"Deepseek Provider is_available(): {self.is_available()}")
        debug_logger.info(f"Deepseek API key exists: {bool(self.api_key)}")
        debug_logger.info(f"Models count: {len(self.models)}")

        # 修复：始终返回加载的模型，不依赖is_available()检查
        # 因为API密钥存在且模型已加载，就应该显示在列表中
        if self.models:
            debug_logger.info(f"返回Deepseek模型: {[model.value for model in self.models]}")
            return self.models
        else:
            debug_logger.warning("Deepseek模型列表为空")
            return []
    
    async def check_connection(self) -> Tuple[bool, str]:
        """检查Deepseek API连接状态"""
        try:
            if not self.api_key:
                return False, "Deepseek API密钥未配置"
            
            await self.initialize()
            
            # 发送测试请求
            test_payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=test_payload
            )
            
            if response.status_code == 200:
                logger.info("Deepseek API连接正常")
                return True, "Deepseek API连接正常"
            else:
                error_msg = self._handle_api_error(response.status_code, response.text)
                logger.error(f"Deepseek API连接失败: {error_msg}")
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Deepseek API连接异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """非流式对话"""
        try:
            await self.initialize()
            
            payload = self._build_deepseek_payload(request, stream=False)
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return self._parse_deepseek_response(result)
            else:
                error_msg = self._handle_api_error(response.status_code, response.text)
                return ChatResponse(
                    id=str(uuid.uuid4()),
                    model=request.model,
                    message=Message(role="assistant", content=f"错误: {error_msg}"),
                    usage={"error": True}
                )
                
        except Exception as e:
            error_msg = f"Deepseek对话请求异常: {str(e)}"
            logger.error(error_msg)
            return ChatResponse(
                id=str(uuid.uuid4()),
                model=request.model,
                message=Message(role="assistant", content=f"异常: {error_msg}"),
                usage={"error": True}
            )
    
    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamEvent, None]:
        """流式对话"""
        try:
            await self.initialize()
            
            payload = self._build_deepseek_payload(request, stream=True)
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                
                if response.status_code != 200:
                    error_msg = self._handle_api_error(response.status_code, await response.aread())
                    yield StreamEvent(type="error", data={"error": error_msg})
                    return
                
                # 处理流式响应
                async for line in response.aiter_lines():
                    if line.strip():
                        if line.startswith('data: '):
                            data_text = line[6:]  # 去掉 'data: ' 前缀
                            
                            if data_text.strip() == '[DONE]':
                                yield StreamEvent(type="done", data={})
                                break
                            
                            try:
                                data = json.loads(data_text)
                                event = self._parse_deepseek_stream_chunk(data)
                                if event:
                                    yield event
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            error_msg = f"Deepseek流式对话异常: {str(e)}"
            logger.error(error_msg)
            yield StreamEvent(type="error", data={"error": error_msg})
    
    def _build_deepseek_payload(self, request: ChatRequest, stream: bool = False) -> Dict[str, Any]:
        """构建Deepseek API请求负载"""
        messages = []
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        payload = {
            "model": request.model,
            "messages": messages,
            "stream": stream,
            "max_tokens": getattr(request, 'max_tokens', self.max_tokens),
            "temperature": getattr(request, 'temperature', 0.7)
        }

        # 对于推理模型，启用思考模式
        if 'reasoner' in request.model or 'think' in request.model.lower():
            logger.info(f"[DeepSeek调试] 检测到推理模型 {request.model}，启用思考模式")
            # 尝试多种可能的推理启用参数
            payload["reasoning"] = True
            payload["enable_reasoning"] = True
            # DeepSeek V3的beta参数格式
            payload["beta"] = {"reasoning": True}
            logger.info(f"[DeepSeek调试] 已添加推理参数: reasoning=True, beta.reasoning=True")

        logger.info(f"[DeepSeek调试] 最终请求payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        return payload
    
    def _parse_deepseek_response(self, response_data: Dict[str, Any]) -> ChatResponse:
        """解析Deepseek响应"""
        choices = response_data.get('choices', [])
        if not choices:
            return ChatResponse(
                id=str(uuid.uuid4()),
                model=response_data.get('model', ''),
                message=Message(role="assistant", content="响应格式错误"),
                usage={"error": True}
            )
        
        message_data = choices[0].get('message', {})
        message = Message(
            role=message_data.get('role', 'assistant'),
            content=message_data.get('content', '')
        )
        
        usage = response_data.get('usage', {})
        
        return ChatResponse(
            id=response_data.get('id', str(uuid.uuid4())),
            model=response_data.get('model', ''),
            message=message,
            usage=usage
        )
    
    def _parse_deepseek_stream_chunk(self, chunk_data: Dict[str, Any]) -> StreamEvent:
        """解析Deepseek流式响应块"""
        # 添加详细的调试日志
        logger.info(f"[DeepSeek调试] 收到流式数据块: {json.dumps(chunk_data, ensure_ascii=False, indent=2)}")

        choices = chunk_data.get('choices', [])
        if not choices:
            logger.warning(f"[DeepSeek调试] 数据块中没有choices字段")
            return None

        delta = choices[0].get('delta', {})
        logger.info(f"[DeepSeek调试] delta内容: {json.dumps(delta, ensure_ascii=False, indent=2)}")

        content = delta.get('content', '')

        # 检测思考内容 - 使用正确的DeepSeek字段名
        reasoning_content = delta.get('reasoning_content', '')

        # 如果有思考内容，返回思考事件
        if reasoning_content:
            logger.info(f"[DeepSeek调试] 找到推理内容: {reasoning_content}")
            return StreamEvent(
                type="thinking",
                data={"thinking": reasoning_content}
            )

        # 如果有普通内容，返回内容事件
        if content:
            logger.info(f"[DeepSeek调试] 返回内容事件: {content}")
            return StreamEvent(
                type="content",
                data={"content": content}
            )

        finish_reason = choices[0].get('finish_reason')
        if finish_reason:
            logger.info(f"[DeepSeek调试] 返回完成事件: {finish_reason}")
            return StreamEvent(
                type="finish",
                data={"reason": finish_reason}
            )

        logger.debug(f"[DeepSeek调试] 无关键内容的数据块，返回None")
        return None