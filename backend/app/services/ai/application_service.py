import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from pydantic import ValidationError

from app.models.ai import (
    ChatRequest,
    Message,
    ModelConnectionStatus,
    ModelsResponse,
    SearchSource,
)
from app.services.ai.base import safe_ai_client_message
from app.services.ai.manager import AIServiceManager
from app.services.ai.prompts import NETWORK_SECURITY_ARCHITECT_PERSONA
from app.services.search.brave_search import BraveSearchClient, SearchResult
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

    def __init__(
        self,
        ai_manager: AIServiceManager,
        brave_client: Optional[BraveSearchClient] = None,
    ):
        self.ai_manager = ai_manager
        self.brave_client = brave_client

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

    def chat_stream(self, request: ChatRequest) -> AIStreamingResult:
        """处理聊天流式请求。"""
        self._ensure_model(request.model)
        self._log_chat_request("接收流式聊天请求", request)
        session_id = f"stream_{int(time.time() * 1000)}"
        logger.info(f"开始新的流式会话: {session_id}")
        request.stream = True

        async def generate_text_stream() -> AsyncIterator[str]:
            try:
                sources, search_failed = await self._maybe_inject_search(request)
                if request.enable_search:
                    yield encode_sse_event(
                        "search_results",
                        {
                            "sources": [s.model_dump() for s in sources],
                            "search_failed": search_failed,
                        },
                    )
                # 注入角色 persona：排在搜索注入之后，使 persona 位于 messages[0]、
                # 搜索上下文顺延其后——稳定人设须优先于临时检索上下文。
                self._inject_persona(request)
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

    def _inject_persona(self, request: ChatRequest) -> None:
        """在消息最前注入「高级网络安全架构师」角色 system，定义 AI 助手稳定人格。

        无条件注入（与 enable_search 无关），并刻意在 _maybe_inject_search 之后调用，
        使最终顺序为 [persona, 搜索上下文?, ...用户消息]——稳定人设须优先于临时检索上下文，
        否则模型容易被后插入的大段搜索文本"盖过"角色设定。
        幂等保护：messages[0] 已是同一 persona 时跳过，避免重复注入。
        """
        if (
            request.messages
            and request.messages[0].role == "system"
            and request.messages[0].content == NETWORK_SECURITY_ARCHITECT_PERSONA
        ):
            return
        request.messages.insert(
            0,
            Message(role="system", content=NETWORK_SECURITY_ARCHITECT_PERSONA),
        )

    async def _maybe_inject_search(
        self,
        request: ChatRequest,
    ) -> tuple[list[SearchSource], bool]:
        """根据 enable_search 调 Brave，并把结果作为 system message 注入到 messages[0]。

        Returns:
            (sources, search_failed)：
              - sources：成功时为非空列表；其他场景为 []
              - search_failed：启用但未取到结果时为 True；未启用 / 成功时为 False
        """
        if not request.enable_search:
            return ([], False)
        if self.brave_client is None or not self.brave_client.is_enabled():
            logger.warning("enable_search=true 但 Brave 未启用，跳过注入")
            return ([], True)

        query = self._extract_query(request.messages)
        if not query:
            return ([], True)

        try:
            raw_results = await self.brave_client.search(query)
        except Exception as exc:  # 防御性兜底；client 已吞异常，这里再加一层
            logger.warning("Brave 搜索调用异常：%s", type(exc).__name__)
            return ([], True)

        if not raw_results:
            return ([], True)

        sources = [
            SearchSource(title=r.title, url=r.url, description=r.description)
            for r in raw_results
        ]
        system_block = self._format_search_block(raw_results, query)
        request.messages.insert(0, Message(role="system", content=system_block))
        return (sources, False)

    @staticmethod
    def _extract_query(messages: list[Message]) -> str:
        """取最后一条 user message 作为搜索 query。"""
        for message in reversed(messages):
            if message.role == "user" and message.content.strip():
                return message.content.strip()
        return ""

    @staticmethod
    def _format_search_block(
        results: list[SearchResult],
        query: str,
        *,
        now: Optional[datetime] = None,
    ) -> str:
        """把 Brave 搜索结果格式化为可注入的 system message 文本。

        头部注入"当前真实时间"作为 temporal grounding：LLM 没有内置时间认知，
        若不显式提供时间锚点，会把搜索结果摘要里出现的某条新闻日期误当作"今天"
        ——这是 LLM 在 web 检索增强场景下经典的时间漂移失败模式。

        二次截断：单条 description 最长 240 字，整体不超过约 4KB。

        Args:
            results: Brave 返回的结构化结果列表。
            query: 原始用户问题。
            now: 测试注入用；None 时取 datetime.now().astimezone() 带本地时区。
        """
        timestamp = (now or datetime.now().astimezone()).isoformat(timespec="seconds")
        lines: list[str] = [
            f"当前真实时间: {timestamp}",
            "请以此时间为准回答涉及\"今天/现在/最新\"等时间敏感问题；",
            "若搜索结果摘要中出现的日期与上面声明的当前时间冲突，应以当前时间为准。",
            "",
            "以下是来自网络的实时检索结果，请优先据此回答用户问题，并在回答末尾用 [n] 引用对应来源：",
            "",
        ]
        budget = 4000  # 字符预算
        for idx, item in enumerate(results, start=1):
            desc = (item.description or "").strip()
            if len(desc) > 240:
                desc = desc[:240] + "…"
            chunk = f"[{idx}] {item.title}\n    URL: {item.url}\n    摘要: {desc}\n"
            if budget - len(chunk) < 0:
                break
            lines.append(chunk)
            budget -= len(chunk)
        lines.append("")
        lines.append(f"用户问题: {query}")
        return "\n".join(lines)


def encode_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """统一编码 SSE 事件，避免裸文本和 data-only 响应混用。"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
