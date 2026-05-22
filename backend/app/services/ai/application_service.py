import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from app.models.ai import (
    ChatRequest,
    ChatResponse,
    DeepseekGenerateRequest,
    Message,
    ModelConnectionStatus,
    ModelsResponse,
)
from app.services.ai.base import safe_ai_client_message
from app.services.ai.manager import AIServiceManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AIApplicationError(Exception):
    """AI 应用服务异常，由路由层映射为 HTTP 响应。"""

    def __init__(self, client_message: str, status_code: int = 500):
        super().__init__(client_message)
        self.client_message = client_message
        self.status_code = status_code


class AIValidationError(AIApplicationError):
    """AI 请求参数验证异常。"""

    def __init__(self, detail: list[dict[str, Any]]):
        super().__init__("请求参数验证失败", status_code=422)
        self.detail = detail


@dataclass(frozen=True)
class AIStreamingResult:
    """需要路由层包装为 StreamingResponse 的流式结果。"""

    chunks: AsyncIterator[str]


class AIApplicationService:
    """AI 应用服务，承载路由之外的对话编排和响应组装。"""

    def __init__(self, ai_manager: AIServiceManager):
        self.ai_manager = ai_manager

    async def get_models_response(self) -> ModelsResponse:
        """获取可用模型响应。"""
        return await self.ai_manager.get_models_response()

    async def check_model_status(self, model_id: str) -> ModelConnectionStatus:
        """检查模型连接状态并脱敏失败原因。"""
        is_connected, message = await self.ai_manager.check_model_status(model_id)
        return ModelConnectionStatus(
            connected=is_connected,
            message=message if is_connected else safe_ai_client_message(message),
            last_check=datetime.now().isoformat(),
        )

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """处理非流式聊天请求。"""
        try:
            self._ensure_model(request.model)
            self._log_chat_request("接收聊天请求", request)
            self._normalize_message_timestamps(request)

            response = await self.ai_manager.chat(request)
            if not getattr(response, "content", None):
                response.content = response.message.content
            return response
        except ValidationError as e:
            raise self._validation_error_from_pydantic(e) from e
        except AIApplicationError:
            raise
        except Exception as e:
            logger.error(f"处理聊天请求时出错: {str(e)}", exc_info=True)
            raise AIApplicationError("内部服务器错误") from e

    def chat_stream(self, request: ChatRequest) -> AIStreamingResult:
        """处理聊天流式请求。"""
        self._ensure_model(request.model)
        self._log_chat_request("接收流式聊天请求", request)
        session_id = f"stream_{int(time.time() * 1000)}"
        logger.info(f"开始新的流式会话: {session_id}")
        request.stream = True

        async def generate_text_stream() -> AsyncIterator[str]:
            try:
                async for event in self.ai_manager.chat_stream(request):
                    if event.type == "content":
                        content = event.data.get("content", "")
                        if content:
                            yield encode_sse_event("content", {"content": content})
                    elif event.type == "thinking":
                        thinking = event.data.get("thinking", "")
                        if thinking:
                            yield encode_sse_event(
                                "thinking",
                                {"thinking": thinking},
                            )
                    elif event.type == "error":
                        error_msg = event.data.get("error", "未知错误")
                        logger.error(f"流式生成内容时出错: {error_msg}")
                        yield encode_sse_event(
                            "error",
                            {"error": safe_ai_client_message(error_msg)},
                        )
                        break
                    elif event.type == "done":
                        logger.info(f"流式会话 {session_id} 已完成")
                        yield encode_sse_event("done", {"done": True})
                        break
            except Exception as e:
                logger.error(f"流式生成内容时出错: {str(e)}", exc_info=True)
                yield encode_sse_event("error", {"error": "内部服务器错误"})

        return AIStreamingResult(generate_text_stream())

    def debug_request_format(self, raw_request: dict[str, Any]) -> dict[str, Any]:
        """解析调试请求格式。"""
        try:
            messages = []
            for msg_data in raw_request.get("messages", []):
                try:
                    msg = Message(**msg_data)
                    messages.append(msg.model_dump())
                except ValidationError as e:
                    messages.append(
                        {
                            "original": msg_data,
                            "errors": str(e),
                        }
                    )

            return {
                "original_request": raw_request,
                "parsed_messages": messages,
                "is_valid": len([m for m in messages if "errors" in m]) == 0,
            }
        except Exception as e:
            logger.error(f"调试请求格式解析失败: {str(e)}", exc_info=True)
            return {
                "error": "解析请求时出错",
                "original_request": raw_request,
            }

    async def check_deepseek_connection(self) -> dict[str, Any]:
        """检查 DeepSeek 兼容状态。"""
        deepseek_models = [
            model
            for model in self.ai_manager.get_available_models()
            if model.value.startswith("deepseek-")
        ]

        if not deepseek_models:
            return {
                "connected": False,
                "message": "未找到Deepseek模型",
                "models": [],
            }

        model_id = deepseek_models[0].value
        is_connected, message = await self.ai_manager.check_model_status(model_id)
        return {
            "connected": is_connected,
            "message": message if is_connected else safe_ai_client_message(message),
            "models": [model.value for model in deepseek_models],
        }

    async def generate_text(
        self,
        payload: DeepseekGenerateRequest,
    ) -> dict[str, Any] | AIStreamingResult:
        """处理 DeepSeek 兼容生成入口。"""
        try:
            request = ChatRequest(
                model=payload.model,
                messages=payload.messages,
                max_tokens=payload.max_tokens,
                temperature=payload.temperature,
                top_p=payload.top_p,
                stream=payload.stream,
            )

            if payload.stream:
                return AIStreamingResult(self._generate_deepseek_stream(request))

            response = await self.ai_manager.chat(request)
            return {
                "content": response.message.content,
                "model": response.model,
                "usage": response.usage,
                "id": getattr(response, "id", None),
            }
        except Exception as e:
            logger.error(f"Deepseek文本生成失败: {str(e)}", exc_info=True)
            raise AIApplicationError("文本生成失败") from e

    async def _generate_deepseek_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """生成 DeepSeek 兼容流式文本。"""
        try:
            async for event in self.ai_manager.chat_stream(request):
                if event.type == "content":
                    content = event.data.get("content", "")
                    if content:
                        yield encode_sse_event("content", {"content": content})
                elif event.type == "done":
                    yield encode_sse_event("done", {"done": True})
                    break
                elif event.type == "error":
                    error_msg = safe_ai_client_message(
                        event.data.get("error", "未知错误")
                    )
                    yield encode_sse_event("error", {"error": error_msg})
                    break
        except Exception as e:
            logger.error(f"Deepseek流式文本生成失败: {str(e)}", exc_info=True)
            yield encode_sse_event("error", {"error": "内部服务器错误"})

    def _ensure_model(self, model: str) -> None:
        if not model:
            raise AIApplicationError("必须指定模型", status_code=400)

    def _log_chat_request(self, action: str, request: ChatRequest) -> None:
        logger.info(f"{action}: 模型={request.model}, 消息数量={len(request.messages)}")
        message_summary = [
            f"[{index}] {message.role}: {len(message.content)} chars"
            for index, message in enumerate(request.messages)
        ]
        logger.debug(f"消息详情: {'; '.join(message_summary)}")

    def _normalize_message_timestamps(self, request: ChatRequest) -> None:
        for message in request.messages:
            if not message.timestamp:
                message.timestamp = None

    def _validation_error_from_pydantic(self, error: ValidationError) -> AIValidationError:
        logger.error(f"请求参数验证错误: {str(error)}")
        detail = [
            {
                "loc": ["body", "request"],
                "msg": f"请求参数验证失败: {str(error)}",
                "type": "value_error",
            }
        ]

        if error.errors():
            first_error = error.errors()[0]
            detail[0]["loc"] = first_error.get("loc", detail[0]["loc"])
            detail[0]["msg"] = (
                f"请求参数验证失败: {first_error.get('msg', str(error))}"
            )

        return AIValidationError(detail)


def encode_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """统一编码 SSE 事件，避免裸文本和 data-only 响应混用。"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
