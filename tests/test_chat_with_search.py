"""ChatRequest.enable_search 注入链路集成测试。

策略：
- 用 AsyncMock 模拟 AIServiceManager.chat / chat_stream，避免真实 provider。
- 用 AsyncMock 模拟 BraveSearchClient，避免真实网络。
- 端到端走 AIApplicationService.chat / chat_stream，断言 system message 注入、
  sources/search_failed 回填、流式响应 yield search_results 事件。
"""

from __future__ import annotations

from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ai import ChatRequest, ChatResponse, Message, StreamEvent
from app.services.ai.application_service import AIApplicationService
from app.services.search.brave_search import SearchResult


def _make_ai_manager_chat_response(content: str = "answer") -> ChatResponse:
    """构造 ai_manager.chat 的返回值。"""
    return ChatResponse(
        message=Message(role="assistant", content=content),
        model="deepseek-v4-flash",
        finish_reason="stop",
        usage={"total_tokens": 10},
    )


def _make_ai_manager(stream_events: list[StreamEvent] | None = None) -> MagicMock:
    """构造 AIServiceManager mock。"""
    ai_manager = MagicMock()
    ai_manager.chat = AsyncMock(return_value=_make_ai_manager_chat_response())

    async def _stream_gen(_req) -> AsyncIterator[StreamEvent]:
        for event in stream_events or []:
            yield event

    ai_manager.chat_stream = _stream_gen
    return ai_manager


def _make_brave_client(
    *,
    enabled: bool = True,
    results: list[SearchResult] | None = None,
) -> MagicMock:
    """构造 BraveSearchClient mock。"""
    client = MagicMock()
    client.is_enabled = MagicMock(return_value=enabled)
    client.search = AsyncMock(return_value=results or [])
    return client


@pytest.mark.asyncio
async def test_chat_with_search_injects_system_and_returns_sources() -> None:
    """enable_search=true + Brave 有结果 → 注入 system + 回填 sources/search_failed=False。"""
    fake_results = [
        SearchResult(title="OSPF 详解", url="https://x.com/ospf", description="链路状态协议"),
        SearchResult(title="OSPF 工作原理", url="https://y.com/ospf", description="SPF 计算"),
    ]
    ai_manager = _make_ai_manager()
    brave = _make_brave_client(enabled=True, results=fake_results)
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="解释 OSPF 协议")],
        enable_search=True,
    )
    response = await service.chat(request)

    # Brave 被调，传入用户最后一条 message
    brave.search.assert_awaited_once()
    call_kwargs = brave.search.await_args
    assert "OSPF" in call_kwargs.args[0] or "OSPF" in str(call_kwargs.kwargs)

    # request.messages 已被前置注入 system
    assert request.messages[0].role == "system"
    assert "OSPF 详解" in request.messages[0].content
    assert "https://x.com/ospf" in request.messages[0].content

    # response 携带 sources + search_failed=False
    assert response.search_failed is False
    assert len(response.sources) == 2
    assert response.sources[0].title == "OSPF 详解"
    assert response.sources[0].url == "https://x.com/ospf"


@pytest.mark.asyncio
async def test_chat_without_enable_search_does_not_call_brave() -> None:
    """enable_search=false → 不调 brave，无 system 注入。"""
    ai_manager = _make_ai_manager()
    brave = _make_brave_client(enabled=True, results=[])
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="今天天气")],
        enable_search=False,
    )
    response = await service.chat(request)

    brave.search.assert_not_called()
    assert request.messages[0].role == "user"
    assert response.sources == []
    assert response.search_failed is False


@pytest.mark.asyncio
async def test_chat_with_search_brave_disabled_marks_failed() -> None:
    """enable_search=true 但 brave.is_enabled()=false → sources=[], search_failed=True。"""
    ai_manager = _make_ai_manager()
    brave = _make_brave_client(enabled=False, results=[])
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="anything")],
        enable_search=True,
    )
    response = await service.chat(request)

    brave.search.assert_not_called()
    assert response.sources == []
    assert response.search_failed is True


@pytest.mark.asyncio
async def test_chat_with_search_empty_results_marks_failed() -> None:
    """enable_search=true + brave 返回 [] → sources=[], search_failed=True，不注入 system。"""
    ai_manager = _make_ai_manager()
    brave = _make_brave_client(enabled=True, results=[])
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="anything")],
        enable_search=True,
    )
    response = await service.chat(request)

    brave.search.assert_awaited_once()
    assert request.messages[0].role == "user"  # 没有 system 注入
    assert response.sources == []
    assert response.search_failed is True


@pytest.mark.asyncio
async def test_chat_with_search_no_brave_client_is_safe() -> None:
    """AIApplicationService 不注入 brave_client（=None）也不应崩溃。"""
    ai_manager = _make_ai_manager()
    service = AIApplicationService(ai_manager, brave_client=None)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="hi")],
        enable_search=True,
    )
    response = await service.chat(request)

    assert response.sources == []
    assert response.search_failed is True


@pytest.mark.asyncio
async def test_chat_stream_yields_search_results_event_first() -> None:
    """流式响应在 LLM 输出前应 yield 一条 search_results 事件。"""
    fake_results = [
        SearchResult(title="t", url="https://t.com", description="d"),
    ]
    stream_events = [
        StreamEvent(type="content", data={"content": "hello"}),
        StreamEvent(type="done", data={"done": True}),
    ]
    ai_manager = _make_ai_manager(stream_events)
    brave = _make_brave_client(enabled=True, results=fake_results)
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="ping")],
        enable_search=True,
        stream=True,
    )
    result = service.chat_stream(request)
    chunks: list[str] = []
    async for chunk in result.chunks:
        chunks.append(chunk)

    # 第一个 chunk 必须是 event: search_results
    assert any("event: search_results" in c for c in chunks)
    first_search_chunk = next(c for c in chunks if "event: search_results" in c)
    assert "https://t.com" in first_search_chunk
    assert '"search_failed": false' in first_search_chunk or '"search_failed":false' in first_search_chunk


@pytest.mark.asyncio
async def test_chat_stream_without_enable_search_no_search_event() -> None:
    """enable_search=false → 流式响应不应出现 search_results 事件。"""
    stream_events = [
        StreamEvent(type="content", data={"content": "hello"}),
        StreamEvent(type="done", data={"done": True}),
    ]
    ai_manager = _make_ai_manager(stream_events)
    brave = _make_brave_client(enabled=True, results=[])
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="ping")],
        enable_search=False,
        stream=True,
    )
    result = service.chat_stream(request)
    chunks: list[str] = []
    async for chunk in result.chunks:
        chunks.append(chunk)

    assert all("event: search_results" not in c for c in chunks)
    brave.search.assert_not_called()


@pytest.mark.asyncio
async def test_extract_query_takes_last_user_message() -> None:
    """有多条 message 时 _extract_query 取最后一条 user。"""
    fake_results = [SearchResult(title="t", url="https://t.com")]
    ai_manager = _make_ai_manager()
    brave = _make_brave_client(enabled=True, results=fake_results)
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[
            Message(role="user", content="first"),
            Message(role="assistant", content="reply"),
            Message(role="user", content="latest question"),
        ],
        enable_search=True,
    )
    await service.chat(request)

    call_args = brave.search.await_args
    query_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("query")
    assert query_arg == "latest question"
