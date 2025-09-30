"""
Anthropic Claude服务提供商实现
处理与Anthropic Claude API的交互
"""

import json
import uuid
from typing import List, Dict, Any, AsyncGenerator, Tuple
import aiohttp

from app.services.ai.base import AIProviderBase, ProviderType
from app.models.ai import AIModel, Message, ChatRequest, ChatResponse, StreamEvent
from app.config.settings import settings
from app.utils.model_config import ModelConfigParser
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ClaudeProvider(AIProviderBase):
    """Anthropic Claude服务提供商"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key, ProviderType.ANTHROPIC)
        self.base_url = settings.ANTHROPIC_API_BASE
        # 从配置动态加载模型
        self.models = ModelConfigParser.parse_claude_models()
        logger.info(f"Claude Provider加载了 {len(self.models)} 个模型")
    
    def get_available_models(self) -> List[AIModel]:
        """获取可用模型列表"""
        return self.models if self.is_available() else []
    
    async def check_connection(self) -> Tuple[bool, str]:
        """检查Claude API连接状态"""
        try:
            if not self.api_key:
                return False, "Claude API密钥未配置"

            await self.initialize()

            # 获取可用模型列表中的第一个模型用于连接测试
            available_models = self.get_available_models()
            if not available_models:
                return False, "未配置可用的Claude模型"

            test_model = available_models[0].value

            # 发送一个简单的测试请求
            headers = self._create_headers({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })

            test_payload = {
                "model": test_model,
                "max_tokens": 1,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }

            async with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=test_payload
            ) as response:
                if response.status == 200:
                    logger.info("Claude API连接正常")
                    return True, "Claude API连接正常"
                else:
                    error_msg = self._handle_api_error(response.status, await response.text())
                    logger.error(f"Claude API连接失败: {error_msg}")
                    return False, error_msg

        except Exception as e:
            error_msg = f"Claude API连接异常: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """非流式对话"""
        try:
            await self.initialize()
            
            payload = self._build_claude_payload(request, stream=False)
            headers = self._create_headers({
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            })
            
            async with self.session.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return self._parse_claude_response(result)
                else:
                    error_msg = self._handle_api_error(response.status, await response.text())
                    return ChatResponse(
                        id=str(uuid.uuid4()),
                        model=request.model,
                        message=Message(role="assistant", content=f"错误: {error_msg}"),
                        usage={"error": True}
                    )
                    
        except Exception as e:
            error_msg = f"Claude对话请求异常: {str(e)}"
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
            
            payload = self._build_claude_payload(request, stream=True)
            headers = self._create_headers({
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Accept": "text/event-stream"
            })
            
            async with self.session.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_msg = self._handle_api_error(response.status, await response.text())
                    yield StreamEvent(type="error", data={"error": error_msg})
                    return
                
                # 处理Claude的Server-Sent Events格式
                async for line in response.content:
                    line_text = line.decode('utf-8').strip()
                    
                    if line_text.startswith('data: '):
                        data_text = line_text[6:]  # 去掉 'data: ' 前缀
                        
                        if data_text == '[DONE]':
                            yield StreamEvent(type="done", data={})
                            break
                        
                        try:
                            data = json.loads(data_text)
                            event = self._parse_claude_stream_chunk(data)
                            if event:
                                yield event
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            error_msg = f"Claude流式对话异常: {str(e)}"
            logger.error(error_msg)
            yield StreamEvent(type="error", data={"error": error_msg})
    
    def _build_claude_payload(self, request: ChatRequest, stream: bool = False) -> Dict[str, Any]:
        """构建Claude API请求负载"""
        messages = []
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        payload = {
            "model": request.model,
            "messages": messages,
            "max_tokens": getattr(request, 'max_tokens', 1000),
            "temperature": getattr(request, 'temperature', 0.7),
            "stream": stream
        }
        
        return payload
    
    def _parse_claude_response(self, response_data: Dict[str, Any]) -> ChatResponse:
        """解析Claude响应"""
        content = response_data.get('content', [])
        
        # Claude的响应格式中，content是一个数组
        message_content = ""
        for block in content:
            if block.get('type') == 'text':
                message_content += block.get('text', '')
        
        message = Message(
            role="assistant",
            content=message_content
        )
        
        usage = response_data.get('usage', {})
        
        return ChatResponse(
            id=response_data.get('id', str(uuid.uuid4())),
            model=response_data.get('model', ''),
            message=message,
            usage=usage
        )
    
    def _parse_claude_stream_chunk(self, chunk_data: Dict[str, Any]) -> StreamEvent:
        """解析Claude流式响应块"""
        event_type = chunk_data.get('type')
        
        if event_type == 'content_block_delta':
            delta = chunk_data.get('delta', {})
            if delta.get('type') == 'text_delta':
                text = delta.get('text', '')
                if text:
                    return StreamEvent(
                        type="content",
                        data={"content": text}
                    )
        
        elif event_type == 'message_stop':
            return StreamEvent(
                type="finish",
                data={"reason": "stop"}
            )
        
        return None