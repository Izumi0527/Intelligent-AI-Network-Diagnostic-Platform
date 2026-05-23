"""Brave Search client 单元测试。

策略：构造函数注入 AsyncMock 模拟的 httpx.AsyncClient，避免真实网络与新增依赖。
覆盖场景：success / 401 / 429 / timeout / disabled / empty-query / 非 JSON / 结构异常。
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.search.brave_search import BraveSearchClient, SearchResult


def _make_response(*, status_code: int = 200, json_data: Any = None) -> MagicMock:
    """构造一个最小化的 httpx.Response mock。"""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    if isinstance(json_data, BaseException):
        response.json.side_effect = json_data
    else:
        response.json.return_value = json_data
    return response


def _make_client(*, get_return=None, get_side_effect=None) -> AsyncMock:
    """构造一个 httpx.AsyncClient mock，get 是 AsyncMock。"""
    client = AsyncMock(spec=httpx.AsyncClient)
    if get_side_effect is not None:
        client.get.side_effect = get_side_effect
    else:
        client.get.return_value = get_return
    return client


@pytest.mark.asyncio
async def test_search_success_returns_parsed_results() -> None:
    """200 + 合法结构 → 返回解析后的 SearchResult 列表。"""
    fake_response = _make_response(
        status_code=200,
        json_data={
            "web": {
                "results": [
                    {
                        "title": "OSPF 协议详解",
                        "url": "https://example.com/ospf",
                        "description": "OSPF 是一种链路状态路由协议",
                    },
                    {
                        "title": "OSPF wikipedia",
                        "url": "https://wiki.example/ospf",
                        "description": "",
                    },
                ]
            }
        },
    )
    fake_client = _make_client(get_return=fake_response)
    brave = BraveSearchClient(
        client=fake_client,
        enabled=True,
        api_key="test-key",
        default_count=5,
    )

    results = await brave.search("OSPF 协议")

    assert len(results) == 2
    assert isinstance(results[0], SearchResult)
    assert results[0].title == "OSPF 协议详解"
    assert results[0].url == "https://example.com/ospf"
    assert results[1].description == ""
    fake_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_401_returns_empty_silently() -> None:
    """401 鉴权失败 → 返回 [] 不抛。"""
    fake_response = _make_response(status_code=401, json_data={"error": "unauthorized"})
    fake_client = _make_client(get_return=fake_response)
    brave = BraveSearchClient(
        client=fake_client, enabled=True, api_key="bad-key"
    )

    results = await brave.search("anything")
    assert results == []


@pytest.mark.asyncio
async def test_search_429_returns_empty_silently() -> None:
    """429 限流 → 返回 [] 不抛。"""
    fake_response = _make_response(status_code=429, json_data={"error": "rate limited"})
    fake_client = _make_client(get_return=fake_response)
    brave = BraveSearchClient(client=fake_client, enabled=True, api_key="k")

    results = await brave.search("foo")
    assert results == []


@pytest.mark.asyncio
async def test_search_timeout_returns_empty_silently() -> None:
    """httpx.TimeoutException → 返回 [] 不抛。"""
    fake_client = _make_client(
        get_side_effect=httpx.TimeoutException("timed out")
    )
    brave = BraveSearchClient(client=fake_client, enabled=True, api_key="k")

    results = await brave.search("foo")
    assert results == []


@pytest.mark.asyncio
async def test_search_disabled_short_circuits_without_calling_client() -> None:
    """enabled=False → 立刻返回 []，不调 client.get。"""
    fake_client = _make_client(get_return=_make_response(status_code=200))
    brave = BraveSearchClient(client=fake_client, enabled=False, api_key="k")

    results = await brave.search("foo")

    assert results == []
    fake_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_search_empty_query_short_circuits() -> None:
    """空 query → 不发起请求。"""
    fake_client = _make_client(get_return=_make_response(status_code=200))
    brave = BraveSearchClient(client=fake_client, enabled=True, api_key="k")

    assert await brave.search("") == []
    assert await brave.search("   ") == []
    fake_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_search_non_json_response_returns_empty() -> None:
    """response.json() 抛 ValueError → 返回 []。"""
    fake_response = _make_response(status_code=200, json_data=ValueError("not json"))
    fake_client = _make_client(get_return=fake_response)
    brave = BraveSearchClient(client=fake_client, enabled=True, api_key="k")

    assert await brave.search("foo") == []


@pytest.mark.asyncio
async def test_search_malformed_structure_returns_empty() -> None:
    """payload.web 缺失 / results 非 list → 返回 []。"""
    fake_response = _make_response(status_code=200, json_data={"unexpected": True})
    fake_client = _make_client(get_return=fake_response)
    brave = BraveSearchClient(client=fake_client, enabled=True, api_key="k")

    assert await brave.search("foo") == []


@pytest.mark.asyncio
async def test_search_skips_results_missing_title_or_url() -> None:
    """缺 title 或 url 的条目应被跳过，不抛。"""
    fake_response = _make_response(
        status_code=200,
        json_data={
            "web": {
                "results": [
                    {"title": "", "url": "https://x.com"},
                    {"title": "ok", "url": ""},
                    {"title": "good", "url": "https://g.com", "description": "d"},
                ]
            }
        },
    )
    fake_client = _make_client(get_return=fake_response)
    brave = BraveSearchClient(client=fake_client, enabled=True, api_key="k")

    results = await brave.search("foo")
    assert len(results) == 1
    assert results[0].title == "good"


@pytest.mark.asyncio
async def test_search_count_is_clamped_to_1_20() -> None:
    """count 超界自动 clamp 到 [1, 20]。"""
    fake_response = _make_response(
        status_code=200, json_data={"web": {"results": []}}
    )
    fake_client = _make_client(get_return=fake_response)
    brave = BraveSearchClient(client=fake_client, enabled=True, api_key="k")

    await brave.search("foo", count=100)
    args, kwargs = fake_client.get.call_args
    assert kwargs["params"]["count"] == 20

    await brave.search("foo", count=0)
    args, kwargs = fake_client.get.call_args
    assert kwargs["params"]["count"] == 1


@pytest.mark.asyncio
async def test_enabled_true_but_empty_api_key_auto_disables() -> None:
    """enabled=true + 空 key → 构造时自动 disable，search 直接返回 []。"""
    brave = BraveSearchClient(enabled=True, api_key="")
    assert brave.is_enabled() is False
    assert await brave.search("foo") == []


@pytest.mark.asyncio
async def test_cleanup_is_safe_when_no_client() -> None:
    """未发起任何请求时 cleanup 也能安全调用。"""
    brave = BraveSearchClient(enabled=False, api_key="k")
    await brave.cleanup()  # 不抛即通过


@pytest.mark.asyncio
async def test_cleanup_does_not_close_injected_client() -> None:
    """注入式 client（owns_client=False）不应被 cleanup 关闭，由调用方管理。"""
    fake_client = _make_client(get_return=_make_response(status_code=200))
    brave = BraveSearchClient(client=fake_client, enabled=True, api_key="k")

    await brave.cleanup()
    fake_client.aclose.assert_not_called()


def test_search_result_to_dict_shape() -> None:
    """SearchResult.to_dict() 必须输出三键。"""
    item = SearchResult(title="t", url="u", description="d")
    assert item.to_dict() == {"title": "t", "url": "u", "description": "d"}
