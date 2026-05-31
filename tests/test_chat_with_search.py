"""ChatRequest.enable_search 注入链路集成测试。

策略：
- 用 MagicMock 模拟 AIServiceManager.chat_stream，避免真实 provider。
- 用 AsyncMock 模拟 BraveSearchClient，避免真实网络。
- 端到端走 AIApplicationService.chat_stream，断言 system message 注入、
  search_results 事件 yield、sources/search_failed 字段值。

历史背景：原版有同时覆盖非流式 service.chat 与流式 service.chat_stream 的测试；
2026-05-28 清理后仅保留流式调用链，所有 Brave Search 注入行为统一通过消费
SSE 事件来验证。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.ai import ChatRequest, Message, StreamEvent
from app.services.ai.application_service import AIApplicationService, AIStreamingResult
from app.services.ai.prompts import NETWORK_SECURITY_ARCHITECT_PERSONA
from app.services.search.brave_search import SearchResult


async def _consume_stream(result: AIStreamingResult) -> list[str]:
    """收集 SSE 流的全部 chunks。"""
    return [chunk async for chunk in result.chunks]


def _extract_search_event(chunks: list[str]) -> dict | None:
    """从 SSE chunks 中提取 search_results 事件的 data JSON，未出现时返回 None。

    SSE 编码格式（见 application_service.encode_sse_event）：
        event: search_results\ndata: {...json...}\n\n
    每个 chunk 是单条事件，data 行不含换行（json.dumps 默认 indent=None）。
    """
    for chunk in chunks:
        if "event: search_results" not in chunk:
            continue
        # data 行的 JSON 在单行内，不需 DOTALL
        match = re.search(r"data:\s*(\{[^\n]*\})", chunk)
        if match:
            return json.loads(match.group(1))
    return None


def _default_stream_events() -> list[StreamEvent]:
    """提供最小可消费的流事件序列，确保 chat_stream 可正常关闭。"""
    return [
        StreamEvent(type="content", data={"content": "ok"}),
        StreamEvent(type="done", data={"done": True}),
    ]


def _make_ai_manager(stream_events: list[StreamEvent] | None = None) -> MagicMock:
    """构造 AIServiceManager mock，仅暴露 chat_stream。"""
    ai_manager = MagicMock()

    events = stream_events if stream_events is not None else _default_stream_events()

    async def _stream_gen(_req) -> AsyncIterator[StreamEvent]:
        for event in events:
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
    """enable_search=true + Brave 有结果 → 注入 system + search_results 事件携带 sources。"""
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
    chunks = await _consume_stream(service.chat_stream(request))

    # Brave 被调，传入用户最后一条 message
    brave.search.assert_awaited_once()
    call_kwargs = brave.search.await_args
    assert "OSPF" in call_kwargs.args[0] or "OSPF" in str(call_kwargs.kwargs)

    # messages[0] 恒为角色 persona；搜索 block 顺延注入为 messages[1]
    assert request.messages[0].content == NETWORK_SECURITY_ARCHITECT_PERSONA
    assert request.messages[1].role == "system"
    assert "OSPF 详解" in request.messages[1].content
    assert "https://x.com/ospf" in request.messages[1].content

    # SSE 事件携带 sources + search_failed=False
    event = _extract_search_event(chunks)
    assert event is not None, "应该有一条 search_results 事件"
    assert event["search_failed"] is False
    assert len(event["sources"]) == 2
    assert event["sources"][0]["title"] == "OSPF 详解"
    assert event["sources"][0]["url"] == "https://x.com/ospf"


@pytest.mark.asyncio
async def test_chat_without_enable_search_does_not_call_brave() -> None:
    """enable_search=false → 不调 brave，无 system 注入，无 search_results 事件。"""
    ai_manager = _make_ai_manager()
    brave = _make_brave_client(enabled=True, results=[])
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="今天天气")],
        enable_search=False,
    )
    chunks = await _consume_stream(service.chat_stream(request))

    brave.search.assert_not_called()
    # persona 注入到 messages[0]，原用户消息顺延；未启用搜索故无搜索 block
    assert request.messages[0].content == NETWORK_SECURITY_ARCHITECT_PERSONA
    assert request.messages[1].role == "user"
    assert _extract_search_event(chunks) is None


@pytest.mark.asyncio
async def test_chat_stream_always_injects_persona_first() -> None:
    """无论是否启用搜索，chat_stream 都应把角色 persona 注入为 messages[0]。"""
    ai_manager = _make_ai_manager()
    service = AIApplicationService(ai_manager, brave_client=None)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="hi")],
        enable_search=False,
    )
    await _consume_stream(service.chat_stream(request))

    assert request.messages[0].role == "system"
    assert request.messages[0].content == NETWORK_SECURITY_ARCHITECT_PERSONA
    # 原用户消息完整保留在 persona 之后
    assert request.messages[1].role == "user"
    assert request.messages[1].content == "hi"


@pytest.mark.asyncio
async def test_chat_with_search_brave_disabled_marks_failed() -> None:
    """enable_search=true 但 brave.is_enabled()=false → search_results 事件 sources=[], search_failed=True。"""
    ai_manager = _make_ai_manager()
    brave = _make_brave_client(enabled=False, results=[])
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="anything")],
        enable_search=True,
    )
    chunks = await _consume_stream(service.chat_stream(request))

    brave.search.assert_not_called()
    event = _extract_search_event(chunks)
    assert event is not None
    assert event["sources"] == []
    assert event["search_failed"] is True


@pytest.mark.asyncio
async def test_chat_with_search_empty_results_marks_failed() -> None:
    """enable_search=true + brave 返回 [] → search_results 事件 sources=[], search_failed=True，不注入 system。"""
    ai_manager = _make_ai_manager()
    brave = _make_brave_client(enabled=True, results=[])
    service = AIApplicationService(ai_manager, brave_client=brave)

    request = ChatRequest(
        model="deepseek-v4-flash",
        messages=[Message(role="user", content="anything")],
        enable_search=True,
    )
    chunks = await _consume_stream(service.chat_stream(request))

    brave.search.assert_awaited_once()
    # 搜索无结果 → 不注入搜索 block；仅有 persona 一条 system，原用户消息顺延其后
    assert request.messages[0].content == NETWORK_SECURITY_ARCHITECT_PERSONA
    assert request.messages[1].role == "user"
    event = _extract_search_event(chunks)
    assert event is not None
    assert event["sources"] == []
    assert event["search_failed"] is True


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
    chunks = await _consume_stream(service.chat_stream(request))

    event = _extract_search_event(chunks)
    assert event is not None
    assert event["sources"] == []
    assert event["search_failed"] is True


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
    await _consume_stream(service.chat_stream(request))

    call_args = brave.search.await_args
    query_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("query")
    assert query_arg == "latest question"


def test_format_search_block_includes_current_time_anchor() -> None:
    """system block 必须包含当前真实时间锚点。

    根因防回归：LLM 没有内置时间认知，若不显式注入真实时间，会把搜索结果摘要
    里出现的某条新闻日期误当作"今天"——这是 temporal grounding 缺失。
    """
    fixed_now = datetime(2026, 5, 23, 22, 54, tzinfo=timezone.utc)
    block = AIApplicationService._format_search_block(
        [SearchResult(title="t", url="https://t.com", description="d")],
        "今天是几号",
        now=fixed_now,
    )

    assert "2026-05-23" in block, "system block 必须包含当前日期"
    assert "当前真实时间" in block, "system block 必须显式声明这是时间锚点"


def test_format_search_block_now_defaults_to_real_now() -> None:
    """未传 now → 应自动使用当前时间，年份必须匹配。"""
    block = AIApplicationService._format_search_block(
        [SearchResult(title="t", url="https://t.com")],
        "query",
    )
    current_year = str(datetime.now().year)
    assert current_year in block
