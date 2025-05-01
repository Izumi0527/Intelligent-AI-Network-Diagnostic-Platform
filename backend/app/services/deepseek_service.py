import logging
import httpx
import asyncio
import json
from typing import Dict, List, Any, Optional, AsyncGenerator, Union, Iterator
from datetime import datetime
import re

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DeepseekService:
    """Deepseek API服务"""
    
    def __init__(self):
        """初始化Deepseek服务"""
        self.api_key = settings.DEEPSEEK_API_KEY
        self.api_url = settings.DEEPSEEK_API_URL
        self.model_version = settings.DEEPSEEK_MODEL_VERSION
        self.timeout = settings.DEEPSEEK_TIMEOUT
        self.max_tokens = settings.DEEPSEEK_MAX_TOKENS
        self.enabled = settings.DEEPSEEK_API_ENABLED

        
        # 可用模型列表
        self.available_models = ["deepseek-reasoner", "deepseek-chat"]
        
        # 初始状态检查
        if not self.api_key:
            logger.warning("未配置Deepseek API密钥，请确保配置有效的API密钥")
        
        # 设置API客户端
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        
        logger.info(f"初始化Deepseek服务: API URL={self.api_url}, 启用状态={self.enabled}")
    
    async def check_connection(self) -> Dict[str, Any]:
        """检查Deepseek API连接状态"""
        if not self.api_key:
            return {
                "status": "error",
                "message": "未配置Deepseek API密钥"
            }
            
        try:
            # 发送简单请求验证连接
            response = await self.client.get(
                f"{self.api_url}/models",
                timeout=5.0
            )
            
            if response.status_code == 200:
                return {
                    "status": "connected",
                    "message": "Deepseek API连接正常",
                    "available_models": self.available_models
                }
            else:
                return {
                    "status": "error",
                    "message": f"Deepseek API连接失败: HTTP {response.status_code}"
                }
                
        except httpx.ConnectError:
            return {
                "status": "error",
                "message": "无法连接到Deepseek API服务器"
            }
            
        except httpx.RequestError as e:
            return {
                "status": "error",
                "message": f"Deepseek API请求错误: {str(e)}"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Deepseek API检查连接时出错: {str(e)}"
            }
    
    async def generate_text(
        self, prompt: str, stream: bool = False, **kwargs
    ) -> Union[AsyncGenerator[str, None], Dict[str, Any]]:
        """
        使用Deepseek API生成文本
        
        Args:
            prompt: 提示文本
            stream: 是否使用流式响应
            **kwargs: 其他参数
            
        Returns:
            流模式: 生成文本的异步生成器
            非流模式: 完整响应字典
        """
        if not self.api_key:
            if stream:
                async def error_stream():
                    yield "错误: 未配置Deepseek API密钥"
                return error_stream()
            else:
                return {"error": "未配置Deepseek API密钥"}
                
        # 检查模型版本是否有效
        model = kwargs.get("model", self.model_version)
        if model not in self.available_models:
            if stream:
                async def error_stream():
                    yield f"错误: 不支持的模型版本 {model}，可用模型包括: {', '.join(self.available_models)}"
                return error_stream()
            else:
                return {
                    "error": f"不支持的模型版本 {model}",
                    "available_models": self.available_models
                }
        
        # 构建请求数据 - 支持直接传入消息列表或单一提示文本
        request_data = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": stream
        }
        
        # 处理消息格式 - 支持多种输入方式
        if isinstance(prompt, list) and all(isinstance(item, dict) for item in prompt):
            # 如果prompt是消息列表，直接使用
            request_data["messages"] = prompt
            logger.info(f"使用传入的消息列表: {len(prompt)} 条消息")
        elif "messages" in kwargs and isinstance(kwargs["messages"], list):
            # 如果通过kwargs传入了messages参数
            request_data["messages"] = kwargs["messages"]
            logger.info(f"使用kwargs传入的消息列表: {len(kwargs['messages'])} 条消息")
        else:
            # 默认情况：将prompt作为用户消息内容
            request_data["messages"] = [{"role": "user", "content": prompt}]
            logger.info(f"创建单一用户消息: {prompt[:30]}...")
        
        logger.debug(f"构建Deepseek请求: model={model}, stream={stream}")
        
        # 根据模式选择处理方法
        if stream:
            return self._generate_stream(request_data)
        else:
            return await self._generate_complete(request_data)
    
    async def _generate_complete(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """完整模式生成文本"""
        try:
            response = await self.client.post(
                f"{self.api_url}/chat/completions",
                json=request_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Deepseek API错误: HTTP {response.status_code}, {response.text}")
                return {
                    "error": f"API错误 {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logger.error(f"Deepseek API请求出错: {str(e)}")
            return {"error": f"API请求失败: {str(e)}"}
    
    async def _generate_stream(self, request_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        生成流式文本，处理并仅返回纯文本内容（不包含原始JSON）
        
        Args:
            request_data: 请求数据
            
        Returns:
            流式生成的文本片段
        """
        logger.debug(f"流式请求DeepSeek API: {request_data['model']}")
        
        try:
            # 同步处理返回的数据，而不是异步的方式，以确保流式响应正常工作
            async with self.client.stream(
                "POST",
                f"{self.api_url}/chat/completions",
                json=request_data,
                timeout=60.0
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Deepseek API流式请求错误: HTTP {response.status_code}, {error_text}")
                    # 返回简单的错误消息，而不是JSON
                    yield f"错误: API返回 {response.status_code}"
                    return
                
                # 使用同步模式处理流式响应
                buffer = b""
                
                # 处理流式响应
                async for chunk in response.aiter_bytes():
                    if not chunk:
                        continue
                        
                    buffer += chunk
                    
                    # 检查是否有完整的事件
                    if b"\n\n" in buffer:
                        parts = buffer.split(b"\n\n")
                        
                        # 处理除最后一个部分外的所有部分
                        for part in parts[:-1]:
                            # 跳过空部分
                            if not part.strip():
                                continue
                            
                            # 特殊处理[DONE]标记
                            if part.strip() == b"data: [DONE]" or part.strip() == b"[DONE]":
                                logger.debug("收到流式响应结束标记 [DONE]")
                                yield "[DONE]"  # 仅发送简单的结束标记
                                continue
                            
                            # 处理SSE格式数据
                            if part.startswith(b"data: "):
                                data_str = part.decode("utf-8", errors="replace")
                                
                                # 解析并提取纯文本内容
                                try:
                                    # 去掉"data: "前缀
                                    json_str = data_str[6:].strip()
                                    if json_str:
                                        json_data = json.loads(json_str)
                                        
                                        # 提取文本内容
                                        if "choices" in json_data and json_data["choices"]:
                                            choice = json_data["choices"][0]
                                            if "delta" in choice and "content" in choice["delta"]:
                                                content = choice["delta"]["content"]
                                                if content:
                                                    # 只返回实际内容，不包含原始JSON
                                                    yield content
                                except json.JSONDecodeError as e:
                                    logger.error(f"解析JSON失败: {e}, 数据: {data_str[:100]}...")
                                    continue
                            else:
                                # 处理非SSE格式数据
                                try:
                                    text = part.decode("utf-8", errors="replace").strip()
                                    if text and text != "[DONE]":
                                        # 非标准格式，尝试提取内容
                                        try:
                                            json_data = json.loads(text)
                                            if "choices" in json_data and json_data["choices"]:
                                                choice = json_data["choices"][0]
                                                if "delta" in choice and "content" in choice["delta"]:
                                                    content = choice["delta"]["content"]
                                                    if content:
                                                        yield content
                                        except json.JSONDecodeError:
                                            # 如果无法解析为JSON，则假设它是纯文本内容
                                            yield text
                                except Exception as e:
                                    logger.error(f"处理非SSE格式数据失败: {e}")
                                    continue
                        
                        # 保留最后一部分用于下一次处理
                        buffer = parts[-1]
                
                # 处理可能遗留在缓冲区中的内容
                if buffer.strip():
                    try:
                        text = buffer.decode("utf-8", errors="replace").strip()
                        if text.startswith("data: "):
                            json_str = text[6:].strip()
                            if json_str and json_str != "[DONE]":
                                try:
                                    json_data = json.loads(json_str)
                                    if "choices" in json_data and json_data["choices"]:
                                        choice = json_data["choices"][0]
                                        if "delta" in choice and "content" in choice["delta"]:
                                            content = choice["delta"]["content"]
                                            if content:
                                                yield content
                                except json.JSONDecodeError:
                                    pass
                    except Exception as e:
                        logger.error(f"处理缓冲区剩余内容时出错: {e}")
        
        except httpx.RequestError as e:
            logger.error(f"Deepseek API请求错误: {str(e)}")
            yield f"错误: API请求失败 - {str(e)}"
        
        except Exception as e:
            logger.error(f"流式生成文本时出错: {str(e)}")
            yield f"错误: {str(e)}"
    
    async def analyze_network_log(self, log_content: str, query: str, model: str = None) -> AsyncGenerator[str, None]:
        """
        分析网络日志
        
        Args:
            log_content: 网络日志内容
            query: 用户查询
            model: 使用的模型名称
            
        Returns:
            生成分析结果的异步生成器
        """
        system_prompt = "你是一名专业的网络工程师和故障排查专家。请分析以下网络日志，并详细解答用户的问题。"
        
        user_content = f"""
## 网络日志
```
{log_content}
```

## 用户问题
{query}
"""
        
        # 传入指定模型，否则使用默认模型
        model_to_use = model if model in self.available_models else self.model_version
        
        # 构建请求数据
        request_data = {
            "model": model_to_use,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.3,
            "max_tokens": self.max_tokens,
            "stream": True
        }
        
        # 调用流式生成
        try:
            async with self.client.stream(
                "POST",
                f"{self.api_url}/chat/completions",
                json=request_data,
                timeout=60.0
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Deepseek API流式请求错误: HTTP {response.status_code}, {error_text}")
                    # 避免嵌套f-string，分两步构建错误消息
                    error_decoded = error_text.decode("utf-8", errors="replace")
                    error_message = f"API返回 {response.status_code} - {error_decoded}"
                    yield f"错误: {error_message}"
                    return
                
                # 处理流式响应
                buffer = b""
                async for chunk in response.aiter_bytes():
                    buffer += chunk
                    if b"\n\n" in buffer:
                        parts = buffer.split(b"\n\n")
                        for part in parts[:-1]:
                            if part.startswith(b"data: "):
                                data = part[6:]  # 去掉前缀
                                if data.strip():
                                    try:
                                        json_data = json.loads(data)
                                        if "choices" in json_data and json_data["choices"]:
                                            choice = json_data["choices"][0]
                                            if "delta" in choice and "content" in choice["delta"]:
                                                text = choice["delta"]["content"]
                                                if text:
                                                    yield text
                                    except json.JSONDecodeError:
                                        logger.warning(f"无法解析流式响应JSON: {data}")
                        
                        buffer = parts[-1]
        
        except asyncio.TimeoutError:
            logger.error("Deepseek API流式请求超时")
            yield "错误: API请求超时"
            
        except Exception as e:
            logger.error(f"Deepseek API流式请求出错: {str(e)}")
            yield f"错误: API请求失败: {str(e)}"
            
    async def _chat_completion_adapter(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将Deepseek的响应适配为与我们平台一致的格式
        
        Args:
            request_data: 请求数据
            
        Returns:
            适配后的响应数据
        """
        try:
            # 调用Deepseek API
            deepseek_response = await self._generate_complete(request_data)
            
            # 检查是否有错误
            if "error" in deepseek_response:
                return {
                    "error": deepseek_response["error"],
                    "details": deepseek_response.get("details", "")
                }
            
            # 从Deepseek响应中提取内容
            assistant_message = "未获取到回复"
            if "choices" in deepseek_response and deepseek_response["choices"]:
                choice = deepseek_response["choices"][0]
                if "message" in choice:
                    assistant_message = choice["message"].get("content", "")
            
            # 构建适配后的响应
            return {
                "message": {
                    "role": "assistant",
                    "content": assistant_message,
                    "timestamp": datetime.now().isoformat()
                },
                "model": request_data["model"],
                "finish_reason": "stop",
                "usage": deepseek_response.get("usage", {})
            }
        
        except Exception as e:
            logger.error(f"适配Deepseek响应时出错: {str(e)}")
            return {
                "error": f"适配响应失败: {str(e)}",
                "details": "服务器内部错误"
            }
    
    async def close(self):
        """关闭客户端连接"""
        if self.client:
            await self.client.aclose()
            logger.info("关闭Deepseek API客户端")

    def generate_text_sync(
        self, prompt: str, stream: bool = False, **kwargs
    ):
        """
        使用Deepseek API生成文本（同步版本）
        
        Args:
            prompt: 提示文本
            stream: 是否使用流式响应
            **kwargs: 其他参数
            
        Returns:
            流模式: 生成文本的同步生成器
            非流模式: 完整响应字典
        """
        if not self.api_key:
            if stream:
                def error_stream():
                    yield "错误: 未配置Deepseek API密钥"
                return error_stream()
            else:
                return {"error": "未配置Deepseek API密钥"}
                
        # 检查模型版本是否有效
        model = kwargs.get("model", self.model_version)
        if model not in self.available_models:
            if stream:
                def error_stream():
                    yield f"错误: 不支持的模型版本 {model}，可用模型包括: {', '.join(self.available_models)}"
                return error_stream()
            else:
                return {
                    "error": f"不支持的模型版本 {model}",
                    "available_models": self.available_models
                }
        
        # 构建请求数据 - 支持直接传入消息列表或单一提示文本
        request_data = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": stream
        }
        
        # 处理消息格式 - 支持多种输入方式
        if isinstance(prompt, list) and all(isinstance(item, dict) for item in prompt):
            # 如果prompt是消息列表，直接使用
            request_data["messages"] = prompt
            logger.info(f"使用传入的消息列表: {len(prompt)} 条消息")
        elif "messages" in kwargs and isinstance(kwargs["messages"], list):
            # 如果通过kwargs传入了messages参数
            request_data["messages"] = kwargs["messages"]
            logger.info(f"使用kwargs传入的消息列表: {len(kwargs['messages'])} 条消息")
        else:
            # 默认情况：将prompt作为用户消息内容
            request_data["messages"] = [{"role": "user", "content": prompt}]
            logger.info(f"创建单一用户消息: {prompt[:30]}...")
        
        logger.debug(f"构建Deepseek同步请求: model={model}, stream={stream}")
        
        # 根据模式选择处理方法
        if stream:
            logger.info(f"开始同步流式请求: 模型={model}, 提示长度={len(prompt)}")
            stream_generator = self._generate_stream_sync(request_data)
            # 包装生成器以确保日志记录
            def wrapped_generator():
                content_yielded = False
                try:
                    for content in stream_generator:
                        content_yielded = True
                        yield content
                    logger.info(f"同步流式请求完成: 模型={model}, 有内容生成={content_yielded}")
                except Exception as e:
                    logger.error(f"同步流式请求出错: {str(e)}")
                    yield f"错误: {str(e)}"
            return wrapped_generator()
        else:
            # 同步模式下，使用event loop运行异步方法
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._generate_complete(request_data))
            finally:
                loop.close()
    
    def _generate_stream_sync(self, request_data: Dict[str, Any]) -> Iterator[str]:
        """
        同步调用DeepSeek API并处理流式响应，只返回纯文本内容。
        逐块处理并立即返回内容，确保流式效果。
        """
        import httpx
        import json
        import logging

        try:
            logger.info(f"开始DeepSeek同步流式请求: 模型={request_data.get('model', '未知')}")
            
            # 获取请求头信息
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 使用httpx处理流式请求
            with httpx.Client(timeout=90.0) as client:
                with client.stream(
                    "POST",
                    f"{self.api_url}/chat/completions",
                    json=request_data,
                    headers=headers
                ) as response:
                    if response.status_code != 200:
                        error_msg = f"DeepSeek API返回错误: HTTP {response.status_code}"
                        logger.error(error_msg)
                        yield f"错误: {error_msg}"
                        return

                    total_content = ""
                    content_count = 0
                    
                    # 逐块处理响应 - 关键改进：立即处理并返回每个块
                    for chunk in response.iter_bytes():
                        if not chunk:
                            continue
                            
                        # 解码为文本
                        chunk_text = chunk.decode("utf-8", errors="replace")
                        
                        # 处理data:前缀的SSE格式
                        if "data:" in chunk_text:
                            lines = chunk_text.split("\n")
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                    
                                if line == "data: [DONE]":
                                    logger.debug("收到流式响应结束标记")
                                    continue
                                    
                                if line.startswith("data:"):
                                    try:
                                        # 提取data:后的JSON
                                        json_str = line[5:].strip()
                                        if json_str and json_str != "[DONE]":
                                            data = json.loads(json_str)
                                            if "choices" in data and data["choices"]:
                                                choice = data["choices"][0]
                                                if "delta" in choice and "content" in choice["delta"]:
                                                    content = choice["delta"]["content"]
                                                    if content:
                                                        # 只返回实际文本内容，立即yield
                                                        total_content += content
                                                        content_count += len(content)
                                                        yield content
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"解析JSON失败: {e}")
                                        continue
                                    except Exception as e:
                                        logger.warning(f"处理数据块时出错: {e}")
                                        continue
                                    
                    # 记录处理结果
                    if content_count > 0:
                        logger.info(f"成功从DeepSeek获取内容，总计{content_count}字符")
                    else:
                        logger.warning("未从DeepSeek获取到任何内容")
                        yield "抱歉，未能获取到回复内容"
                    
                    logger.info("DeepSeek同步流式请求完成")
        
        except Exception as e:
            logger.error(f"DeepSeek同步流式请求发生异常: {str(e)}")
            yield f"错误: {str(e)}"
    
    async def generate_text_async(self, prompt: str, stream: bool = False, **kwargs):
        """与generate_text相同，但名称更明确，表示异步方法"""
        return await self.generate_text(prompt, stream, **kwargs) 