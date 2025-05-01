import json
import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
import aiohttp
from datetime import datetime

from app.models.ai import (
    AIModel, Message, ChatRequest, ChatResponse, 
    ModelConnectionStatus, ModelsResponse, StreamEvent
)
from app.config.settings import settings
from app.services.deepseek_service import DeepseekService
from app.utils.logger import get_logger

logger = get_logger(__name__)

class AIService:
    """AI服务，处理与不同AI模型的交互"""
    
    def __init__(self, deepseek_service: DeepseekService):
        """初始化AI服务"""
        # 依赖注入其他服务
        self.deepseek_service = deepseek_service
        
        # 保存API密钥，用于直接调用不同服务的API
        self.api_keys = {
            "openai": settings.OPENAI_API_KEY,
            "anthropic": settings.ANTHROPIC_API_KEY,
            "deepseek": settings.DEEPSEEK_API_KEY
        }
        
        # 加载可用模型
        self.available_models = self._load_available_models()
        logger.info(f"AI服务初始化完成，加载了 {len(self.available_models)} 个可用模型")
    
    def _load_available_models(self) -> List[AIModel]:
        """加载可用的AI模型信息"""
        # 这里应从配置或数据库加载实际可用的模型
        # 当前为演示，直接硬编码返回支持的模型列表
        
        # 检查API密钥可用性
        has_openai_key = bool(self.api_keys.get("openai"))
        has_anthropic_key = bool(self.api_keys.get("anthropic"))
        has_deepseek_key = bool(self.api_keys.get("deepseek"))
        
        logger.info(f"API密钥可用性检查: OpenAI={has_openai_key}, Anthropic={has_anthropic_key}, Deepseek={has_deepseek_key}")
        
        # 基于API密钥可用性过滤模型
        models = []
        
        # Anthropic模型
        if has_anthropic_key:
            models.extend([
                AIModel(
                    value="claude-3.7-sonnet-20240229",
                    label="Claude 3.7",
                    description="最新的Claude 3.7模型，强大的推理能力和上下文理解",
                    features=["智能推理", "问题解答", "上下文分析"],
                    max_tokens=200000
                ),
                AIModel(
                    value="claude-3-sonnet-20240229",
                    label="Claude 3 Sonnet",
                    description="Claude 3系列的平衡模型，适合大多数任务",
                    features=["内容生成", "问题解答", "代码生成"],
                    max_tokens=180000
                ),
                AIModel(
                    value="claude-3.5-sonnet-20240620",
                    label="Claude 3.5 Sonnet",
                    description="Claude 3.5系列模型，增强的分析能力",
                    features=["复杂分析", "文本处理", "专业解答"],
                    max_tokens=180000
                ),
            ])
        
        # OpenAI模型
        if has_openai_key:
            models.append(
                AIModel(
                    value="gpt-4o",
                    label="GPT-4o",
                    description="OpenAI的最新多模态模型，擅长多种任务",
                    features=["通用AI", "代码生成", "问题解答"],
                    max_tokens=128000
                ),
            )
        
        # Deepseek模型 - 无论密钥是否可用，都添加这些模型，因为可能使用环境变量配置
        models.extend([
            AIModel(
                value="deepseek-chat",
                label="DeepSeek-V3-0324",
                description="DeepSeek的中文大模型，擅长处理中文网络问题分析",
                features=["网络设备故障分析", "中文交互", "配置分析"],
                max_tokens=16000
            ),
            AIModel(
                value="deepseek-reasoner",
                label="DeepSeek-R1",
                description="DeepSeek的推理型大模型，适合复杂逻辑分析",
                features=["复杂推理", "配置分析", "性能优化"],
                max_tokens=16000
            ),
        ])
        
        return models
    
    async def get_available_models(self) -> ModelsResponse:
        """获取可用的AI模型列表"""
        return ModelsResponse(models=self.available_models)
    
    async def check_model_connection(self, model_id: str) -> ModelConnectionStatus:
        """检查特定模型的连接状态"""
        logger.info(f"检查模型连接: {model_id}")
        
        # 检查模型是否在支持列表中
        model_exists = any(model.value == model_id for model in self.available_models)
        if not model_exists:
            logger.warning(f"请求的模型不存在: {model_id}")
            return ModelConnectionStatus(
                connected=False,
                model=model_id,
                message=f"不支持的模型: {model_id}"
            )
        
        # 根据模型类型调用不同的连接检查
        if model_id.startswith("claude"):
            # Anthropic模型检查
            if not self.api_keys["anthropic"]:
                return ModelConnectionStatus(
                    connected=False,
                    model=model_id,
                    message="未配置Anthropic API密钥"
                )
            # TODO: 实现Anthropic API连接检查
            return ModelConnectionStatus(
                connected=True,
                model=model_id,
                message="Anthropic API连接正常"
            )
            
        elif model_id.startswith("gpt"):
            # OpenAI模型检查
            if not self.api_keys["openai"]:
                return ModelConnectionStatus(
                    connected=False,
                    model=model_id,
                    message="未配置OpenAI API密钥"
                )
            # TODO: 实现OpenAI API连接检查
            return ModelConnectionStatus(
                connected=True,
                model=model_id,
                message="OpenAI API连接正常"
            )
            
        elif model_id.startswith("deepseek"):
            # Deepseek模型检查
            deepseek_status = await self.deepseek_service.check_connection()
            return ModelConnectionStatus(
                connected=deepseek_status.get("status") == "connected",
                model=model_id,
                message=deepseek_status.get("message", "未知状态")
            )
            
        else:
            # 未知模型类型
            return ModelConnectionStatus(
                connected=False,
                model=model_id,
                message=f"未知模型类型: {model_id}"
            )
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """非流式聊天API"""
        try:
            logger.info(f"处理聊天请求: 模型={request.model}, 消息数={len(request.messages)}")
            
            # 根据模型类型调用相应的API
            if request.model.startswith("claude"):
                return await self._call_anthropic_api(request)
                
            elif request.model.startswith("gpt"):
                return await self._call_openai_api_sync(request)
                
            elif request.model.startswith("deepseek"):
                return await self._call_deepseek_api_sync(request)
                
            else:
                logger.error(f"不支持的模型类型: {request.model}")
                raise ValueError(f"不支持的模型类型: {request.model}")
        
        except Exception as e:
            logger.error(f"聊天处理出错: {str(e)}")
            # 创建错误响应
            return ChatResponse(
                message=Message(
                    role="assistant",
                    content=f"处理请求时出错: {str(e)}",
                    timestamp=datetime.now()
                ),
                model=request.model,
                finish_reason="error",
                usage={}
            )
    
    async def chat_stream(self, request: ChatRequest) -> AsyncGenerator[StreamEvent, None]:
        """流式聊天API"""
        try:
            logger.info(f"处理流式聊天请求: 模型={request.model}, 消息数={len(request.messages)}")
            
            # 发送开始事件
            yield StreamEvent(
                event="message_start",
                data={
                    "model": request.model,
                    "message_id": "msg_" + str(int(datetime.now().timestamp())),
                }
            )
            
            # 发送内容块开始事件
            yield StreamEvent(
                event="content_block_start",
                data={
                    "type": "text",
                    "index": 0
                }
            )
            
            # 根据模型类型调用相应的流式API
            if request.model.startswith("claude"):
                async for content in self._call_anthropic_api_stream(request):
                    yield StreamEvent(
                        event="content_block_delta",
                        data={
                            "delta": {"text": content},
                            "index": 0
                        }
                    )
                    
            elif request.model.startswith("gpt"):
                async for content in self._call_openai_api_stream(request):
                    yield StreamEvent(
                        event="content_block_delta",
                        data={
                            "delta": {"text": content},
                            "index": 0
                        }
                    )
                    
            elif request.model.startswith("deepseek"):
                async for content in self._call_deepseek_api_stream(request):
                    yield StreamEvent(
                        event="content_block_delta",
                        data={
                            "delta": {"text": content},
                            "index": 0
                        }
                    )
                    
            else:
                # 不支持的模型类型
                yield StreamEvent(
                    event="error",
                    data={"error": f"不支持的模型类型: {request.model}"}
                )
                return
                
            # 发送内容块结束事件
            yield StreamEvent(
                event="content_block_stop",
                data={"index": 0}
            )
            
            # 发送消息结束事件
            yield StreamEvent(
                event="message_stop",
                data={
                    "message_id": "msg_" + str(int(datetime.now().timestamp())),
                    "usage": {
                        "input_tokens": 0,  # 实际应用中应从API响应获取
                        "output_tokens": 0
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"流式聊天处理出错: {str(e)}")
            # 发送错误事件
            yield StreamEvent(
                event="error",
                data={"error": f"处理请求时出错: {str(e)}"}
            )
    
    def chat_stream_sync(self, request: ChatRequest):
        """同步生成聊天流响应"""
        try:
            # 记录请求
            model = request.model
            messages = request.messages
            
            logger.info(f"开始同步流式响应生成，模型: {model}")
            
            # 根据模型类型调用相应的API
            if model.startswith("claude"):
                # 使用Anthropic API
                for content in self._call_anthropic_api_stream_sync(request):
                    yield content
                    
            elif model.startswith("gpt"):
                # 使用OpenAI API
                for content in self._call_openai_api_stream_sync(request):
                    yield content
                    
            elif model.startswith("deepseek"):
                # 使用Deepseek API
                for content in self._call_deepseek_api_stream_sync(request):
                    yield content
                    
            else:
                logger.error(f"不支持的模型类型: {model}")
                yield f"错误: 不支持的模型类型: {model}"
            
            logger.info("同步流式响应生成完成")
        
        except Exception as e:
            logger.error(f"同步流式响应生成错误: {str(e)}")
            yield f"错误: {str(e)}"
    
    def _clean_stream_content(self, content: str) -> str:
        """清理流式内容，确保返回纯文本，去除所有SSE格式和JSON"""
        if not content or not isinstance(content, str):
            return ""
        
        # 清理所有data:前缀
        clean_content = content
        
        # 1. 递归清理data:前缀
        prev_len = -1
        while prev_len != len(clean_content):
            prev_len = len(clean_content)
            clean_content = clean_content.replace("data:", "")
        
        # 2. 检查是否含有JSON格式的内容，尝试提取文本
        if (clean_content.strip().startswith("{") and 
            ("delta" in clean_content or "content" in clean_content or "text" in clean_content)):
            try:
                data = json.loads(clean_content)
                # Claude格式
                if "event" in data and data["event"] == "content_block_delta":
                    if "data" in data and "delta" in data["data"] and "text" in data["data"]["delta"]:
                        return data["data"]["delta"]["text"]
                # OpenAI/DeepSeek格式
                elif "choices" in data and len(data["choices"]) > 0:
                    if "delta" in data["choices"][0] and "content" in data["choices"][0]["delta"]:
                        return data["choices"][0]["delta"]["content"]
                # 其他格式，尝试找到text或content字段
                elif "text" in data:
                    return data["text"]
                elif "content" in data:
                    return data["content"]
            except:
                # JSON解析失败，继续使用清理后的内容
                pass
        
        # 3. 如果清理后的内容仍包含可疑的JSON标记，使用正则表达式提取有效文本
        if "{" in clean_content or "}" in clean_content:
            import re
            text_matches = re.findall(r'[\u4e00-\u9fa5A-Za-z0-9.,?!，。？！：:;；""''（）()\s]+', clean_content)
            if text_matches:
                clean_content = ' '.join(text_matches)
        
        return clean_content
    
    async def _call_anthropic_api(self, request: ChatRequest) -> ChatResponse:
        """调用Anthropic API进行聊天"""
        if not self.api_keys["anthropic"]:
            return ChatResponse(
                message=Message(
                    role="assistant",
                    content="缺少Anthropic API密钥",
                    timestamp=datetime.now()
                ),
                model=request.model,
                finish_reason="error",
                usage={}
            )
            
        api_url = "https://api.anthropic.com/v1/messages"
        
        # 将我们的消息格式转换为Anthropic API格式
        anthropic_messages = []
        for msg in request.messages:
            anthropic_messages.append({
                "role": msg.role,
                "content": msg.content
            })
            
        payload = {
            "model": request.model,
            "messages": anthropic_messages,
            "stream": request.stream,
            "max_tokens": 4000
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_keys["anthropic"],
            "anthropic-version": "2023-06-01"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return ChatResponse(
                            message=Message(
                                role="assistant",
                                content=f"Anthropic API错误: {response.status}, {error_text}",
                                timestamp=datetime.now()
                            ),
                            model=request.model,
                            finish_reason="error",
                            usage={}
                        )
                        
                    if request.stream:
                        # 处理流式响应
                        response_text = ""
                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if not line or line == "data: [DONE]":
                                continue
                                
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    if "delta" in data and "text" in data["delta"]:
                                        response_text += data["delta"]["text"]
                                except json.JSONDecodeError:
                                    return ChatResponse(
                                        message=Message(
                                            role="assistant",
                                            content=f"无法解析响应: {line}",
                                            timestamp=datetime.now()
                                        ),
                                        model=request.model,
                                        finish_reason="error",
                                        usage={}
                                    )
                    else:
                        # 处理非流式响应
                        data = await response.json()
                        if "content" in data and len(data["content"]) > 0:
                            response_text = data["content"][0]["text"]
                        
            return ChatResponse(
                message=Message(
                    role="assistant",
                    content=response_text,
                    timestamp=datetime.now()
                ),
                model=request.model,
                finish_reason="stop",
                usage={
                    "prompt_tokens": 0,  # 实际应用中应从模型响应获取
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            )
        except Exception as e:
            logger.error(f"调用Anthropic API时出错: {str(e)}")
            return ChatResponse(
                message=Message(
                    role="assistant",
                    content=f"调用AI服务时出错: {str(e)}",
                    timestamp=datetime.now()
                ),
                model=request.model,
                finish_reason="error",
                usage={}
            )
    
    async def _call_openai_api_sync(self, request: ChatRequest) -> ChatResponse:
        """调用OpenAI API进行聊天（同步模式）"""
        if not self.api_keys["openai"]:
            return ChatResponse(
                message=Message(
                    role="assistant",
                    content="缺少OpenAI API密钥",
                    timestamp=datetime.now()
                ),
                model=request.model,
                finish_reason="error",
                usage={}
            )
            
        api_url = "https://api.openai.com/v1/chat/completions"
        
        # 将我们的消息格式转换为OpenAI API格式
        openai_messages = []
        for msg in request.messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })
            
        payload = {
            "model": request.model,
            "messages": openai_messages,
            "stream": request.stream,
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_keys['openai']}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return ChatResponse(
                            message=Message(
                                role="assistant",
                                content=f"OpenAI API错误: {response.status}, {error_text}",
                                timestamp=datetime.now()
                            ),
                            model=request.model,
                            finish_reason="error",
                            usage={}
                        )
                        
                    if request.stream:
                        # 处理流式响应
                        response_text = ""
                        async for line in response.content:
                            line = line.decode("utf-8").strip()
                            if not line or line == "data: [DONE]":
                                continue
                                
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])
                                    if "choices" in data and len(data["choices"]) > 0:
                                        delta = data["choices"][0].get("delta", {})
                                        if "content" in delta:
                                            response_text += delta["content"]
                                except json.JSONDecodeError:
                                    return ChatResponse(
                                        message=Message(
                                            role="assistant",
                                            content=f"无法解析响应: {line}",
                                            timestamp=datetime.now()
                                        ),
                                        model=request.model,
                                        finish_reason="error",
                                        usage={}
                                    )
                    else:
                        # 处理非流式响应
                        data = await response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            content = data["choices"][0]["message"].get("content", "")
                            if content:
                                response_text = content
                        
            return ChatResponse(
                message=Message(
                    role="assistant",
                    content=response_text,
                    timestamp=datetime.now()
                ),
                model=request.model,
                finish_reason="stop",
                usage={
                    "prompt_tokens": 0,  # 实际应用中应从模型响应获取
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            )
        except Exception as e:
            logger.error(f"调用OpenAI API时出错: {str(e)}")
            return ChatResponse(
                message=Message(
                    role="assistant",
                    content=f"调用AI服务时出错: {str(e)}",
                    timestamp=datetime.now()
                ),
                model=request.model,
                finish_reason="error",
                usage={}
            )
    
    async def _call_deepseek_api_sync(self, request: ChatRequest) -> ChatResponse:
        """调用Deepseek API进行聊天（同步模式）"""
        try:
            logger.info(f"调用Deepseek API: 模型={request.model}, 消息数={len(request.messages)}")
            
            # 准备Deepseek API请求
            # 将我们的消息格式转换为Deepseek API格式
            deepseek_messages = []
            for msg in request.messages:
                deepseek_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # 调用Deepseek服务
            response = await self.deepseek_service._generate_complete({
                "model": request.model,
                "messages": deepseek_messages,
                "stream": False
            })
            
            # 检查错误
            if "error" in response:
                logger.error(f"Deepseek API错误: {response['error']}")
                return ChatResponse(
                    message=Message(
                        role="assistant",
                        content=f"Deepseek API错误: {response.get('error')}",
                        timestamp=datetime.now()
                    ),
                    model=request.model,
                    finish_reason="error",
                    usage={}
                )
            
            # 从响应中提取内容
            content = ""
            if "choices" in response and response["choices"]:
                message = response["choices"][0].get("message", {})
                content = message.get("content", "")
            
            # 构建响应
            return ChatResponse(
                message=Message(
                    role="assistant",
                    content=content,
                    timestamp=datetime.now()
                ),
                model=request.model,
                finish_reason="stop",
                usage=response.get("usage", {})
            )
            
        except Exception as e:
            logger.error(f"调用Deepseek API出错: {str(e)}")
            return ChatResponse(
                message=Message(
                    role="assistant",
                    content=f"调用Deepseek API出错: {str(e)}",
                    timestamp=datetime.now()
                ),
                model=request.model,
                finish_reason="error",
                usage={}
            )
    
    async def _call_anthropic_api_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """流式调用Anthropic API"""
        if not self.api_keys["anthropic"]:
            yield "错误: 缺少Anthropic API密钥"
            return
            
        api_url = "https://api.anthropic.com/v1/messages"
        
        # 将我们的消息格式转换为Anthropic API格式
        anthropic_messages = []
        for msg in request.messages:
            anthropic_messages.append({
                "role": msg.role,
                "content": msg.content
            })
            
        payload = {
            "model": request.model,
            "messages": anthropic_messages,
            "stream": True,
            "max_tokens": 4000
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_keys["anthropic"],
            "anthropic-version": "2023-06-01"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"API错误 ({response.status}): {error_text}"
                        return
                        
                    # 处理流式响应
                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if not line or line == "data: [DONE]":
                            continue
                            
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if "delta" in data and "text" in data["delta"]:
                                    yield data["delta"]["text"]
                            except json.JSONDecodeError:
                                yield f"错误: 无法解析响应 - {line}"
                                
        except Exception as e:
            logger.error(f"流式调用Anthropic API时出错: {str(e)}")
            yield f"错误: {str(e)}"
    
    def _call_anthropic_api_stream_sync(self, request: ChatRequest):
        """同步流式调用Anthropic API - 修复版本"""
        if not self.api_keys["anthropic"]:
            yield "错误: 缺少Anthropic API密钥"
            return
        
        import requests
        import json
        
        api_url = "https://api.anthropic.com/v1/messages"
        
        # 转换消息格式为Anthropic API格式
        anthropic_messages = []
        for msg in request.messages:
            anthropic_messages.append({
                "role": "assistant" if msg.role == "assistant" else "user",
                "content": msg.content
            })
        
        # 设置Anthropic API请求参数
        payload = {
            "model": request.model,
            "messages": anthropic_messages,
            "stream": True,
            "max_tokens": 4000
        }
        
        # Anthropic API需要特定的头部格式
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_keys["anthropic"],
            "anthropic-version": "2023-06-01"
        }
        
        try:
            with requests.post(api_url, json=payload, headers=headers, stream=True) as response:
                if response.status_code != 200:
                    yield f"API错误 ({response.status_code}): {response.text}"
                    return
                    
                # 处理流式响应
                for line in response.iter_lines():
                    if not line:
                        continue
                        
                    line = line.decode("utf-8").strip()
                    
                    # 跳过控制消息
                    if line == "data: [DONE]" or not line.startswith("data: "):
                        continue
                        
                    try:
                        # 只提取实际的文本内容
                        data = json.loads(line[6:])  # 跳过"data: "前缀
                        
                        # Claude API的内容结构
                        if "type" in data and data["type"] == "content_block_delta":
                            if "delta" in data and "text" in data["delta"]:
                                # 只返回纯文本内容
                                yield data["delta"]["text"]
                    except json.JSONDecodeError:
                        # 如果解析失败，返回错误但继续处理
                        logger.warning(f"解析Claude响应失败: {line}")
                    except Exception as e:
                        logger.error(f"处理Claude流数据时出错: {str(e)}")
                        
            logger.info("Claude流式响应处理完成")
                    
        except Exception as e:
            logger.error(f"Claude API请求失败: {str(e)}")
            yield f"错误: {str(e)}"
    
    async def _call_openai_api_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """流式调用OpenAI API"""
        if not self.api_keys["openai"]:
            yield "错误: 缺少OpenAI API密钥"
            return
            
        api_url = "https://api.openai.com/v1/chat/completions"
        
        # 将我们的消息格式转换为OpenAI API格式
        openai_messages = []
        for msg in request.messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })
            
        payload = {
            "model": request.model,
            "messages": openai_messages,
            "stream": True,
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_keys['openai']}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"API错误 ({response.status}): {error_text}"
                        return
                        
                    # 处理流式响应
                    async for line in response.content:
                        line = line.decode("utf-8").strip()
                        if not line or line == "data: [DONE]":
                            continue
                            
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                yield f"错误: 无法解析响应 - {line}"
                            
        except Exception as e:
            logger.error(f"流式调用OpenAI API时出错: {str(e)}")
            yield f"错误: {str(e)}"
    
    def _call_openai_api_stream_sync(self, request: ChatRequest):
        """同步流式调用OpenAI API"""
        if not self.api_keys["openai"]:
            yield "错误: 缺少OpenAI API密钥"
            return
            
        import requests
        
        api_url = "https://api.openai.com/v1/chat/completions"
        
        # 将我们的消息格式转换为OpenAI API格式
        openai_messages = []
        for msg in request.messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content
            })
            
        payload = {
            "model": request.model,
            "messages": openai_messages,
            "stream": True,
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_keys['openai']}"
        }
        
        try:
            # 使用同步请求库
            with requests.post(api_url, json=payload, headers=headers, stream=True) as response:
                if response.status_code != 200:
                    yield f"API错误 ({response.status_code}): {response.text}"
                    return
                    
                # 处理流式响应
                for line in response.iter_lines():
                    if not line:
                        continue
                        
                    line = line.decode("utf-8").strip()
                    if not line or line == "data: [DONE]":
                        continue
                        
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                        except json.JSONDecodeError:
                            yield f"错误: 无法解析响应 - {line}"
                        
        except Exception as e:
            logger.error(f"同步流式调用OpenAI API时出错: {str(e)}")
            yield f"错误: {str(e)}"
    
    async def _call_deepseek_api_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """流式调用Deepseek API"""
        try:
            # 提取最后一条用户消息作为提示
            user_messages = [msg for msg in request.messages if msg.role == "user"]
            if not user_messages:
                yield "错误: 至少需要一条用户消息"
                return
            
            prompt = user_messages[-1].content
            model_name = "deepseek-chat"  # 默认模型
            
            if request.model == "deepseek-reasoner":
                model_name = "deepseek-reasoner"
            
            # 调用Deepseek服务
            async for content in self.deepseek_service.generate_text_async(
                prompt, stream=True, model=model_name
            ):
                yield content
                
        except Exception as e:
            logger.error(f"流式调用Deepseek API时出错: {str(e)}")
            yield f"错误: {str(e)}"
    
    def _call_deepseek_api_stream_sync(self, request: ChatRequest):
        """同步流式调用Deepseek API"""
        try:
            # 提取最后一条用户消息作为提示
            user_messages = [msg for msg in request.messages if msg.role == "user"]
            if not user_messages:
                yield "错误: 至少需要一条用户消息"
                return
            
            prompt = user_messages[-1].content
            model_name = "deepseek-chat"  # 默认模型
            
            if request.model == "deepseek-reasoner":
                model_name = "deepseek-reasoner"
            
            # 调用Deepseek服务的同步方法
            for content in self.deepseek_service.generate_text_sync(
                prompt, stream=True, model=model_name
            ):
                # 确保清理任何可能的data:前缀
                if content and isinstance(content, str):
                    # 多重保障：重复清理data:前缀
                    clean_content = content
                    # 递归清理，直到没有data:前缀
                    prev_len = 0
                    while prev_len != len(clean_content):
                        prev_len = len(clean_content)
                        clean_content = clean_content.replace("data:", "")
                    
                    # 检查并删除特殊情况：空格+data:
                    clean_content = clean_content.replace(" data:", "")
                    
                    # 纯文本验证：如果仍包含data:，使用提取纯文本策略
                    if "data:" in clean_content:
                        # 使用正则表达式提取所有有效文本内容
                        import re
                        text_matches = re.findall(r'[\u4e00-\u9fa5A-Za-z0-9.,?!，。？！：:;；""''（）()\s]+', clean_content)
                        if text_matches:
                            clean_content = ' '.join(text_matches)
                    
                    # 最终确认：不存在data:前缀
                    logger.debug(f"返回清理后的内容: '{clean_content[:30]}...'")
                    yield clean_content
                
        except Exception as e:
            logger.error(f"同步流式调用Deepseek API时出错: {str(e)}")
            yield f"错误: {str(e)}" 