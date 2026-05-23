"""Brave Search 客户端。

封装 Brave Search Web API 调用：
- 单例长连接 httpx.AsyncClient（可选注入，便于测试）
- 失败静默：401 / 429 / timeout / 网络异常 一律返回 []，不抛
- 日志脱敏：不在任何日志里打印 api_key
- enabled 开关：未启用时直接返回 []

参考 plan: docs/plans/2026-05-23 1-ai-2-bing-tranquil-cat.md §T2.1
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class SearchResult:
    """单条搜索结果。"""

    title: str
    url: str
    description: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"title": self.title, "url": self.url, "description": self.description}


class BraveSearchClient:
    """Brave Search Web API client。"""

    DEFAULT_BASE_URL = "https://api.search.brave.com/res/v1"

    def __init__(
        self,
        *,
        client: Optional[httpx.AsyncClient] = None,
        enabled: Optional[bool] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_count: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> None:
        """构造：所有参数可选，缺省读取 settings。

        Args:
            client: 注入外部 httpx.AsyncClient（测试时传 mock）。
            enabled / api_key / base_url / default_count / timeout: 显式覆盖 settings。
        """
        self._enabled: bool = (
            enabled if enabled is not None
            else bool(getattr(settings, "BRAVE_SEARCH_ENABLED", False))
        )
        self._api_key: str = (
            api_key if api_key is not None
            else (getattr(settings, "BRAVE_SEARCH_API_KEY", "") or "")
        )
        self._base_url: str = (
            base_url if base_url is not None
            else (getattr(settings, "BRAVE_SEARCH_BASE_URL", "") or self.DEFAULT_BASE_URL)
        ).rstrip("/")
        self._default_count: int = (
            default_count if default_count is not None
            else int(getattr(settings, "BRAVE_SEARCH_DEFAULT_COUNT", 5) or 5)
        )
        self._timeout: float = float(
            timeout if timeout is not None
            else (getattr(settings, "BRAVE_SEARCH_TIMEOUT", 5) or 5)
        )

        # enabled=true 但 key 空 → 自动 disable + warn（settings 层也会校验，这里是双保险）
        if self._enabled and not self._api_key:
            logger.warning("BRAVE_SEARCH_ENABLED=true 但 BRAVE_SEARCH_API_KEY 为空，自动禁用")
            self._enabled = False

        self._client: Optional[httpx.AsyncClient] = client
        self._owns_client: bool = client is None

    def is_enabled(self) -> bool:
        """是否启用联网搜索。"""
        return self._enabled

    async def _ensure_client(self) -> httpx.AsyncClient:
        """懒初始化内部 client（仅在未注入时）。"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self._api_key,
                },
            )
        return self._client

    async def search(
        self,
        query: str,
        *,
        count: Optional[int] = None,
    ) -> list[SearchResult]:
        """执行搜索；失败一律返回 []。

        Args:
            query: 搜索关键词（已去空白）。空 query 直接返回 []。
            count: 返回结果数，None 走 default_count。

        Returns:
            list[SearchResult]：成功返回非空列表；任何失败返回 []。
        """
        if not self._enabled:
            return []

        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        effective_count = max(1, min(20, self._default_count if count is None else count))
        params = {"q": normalized_query, "count": effective_count}

        try:
            client = await self._ensure_client()
            response = await client.get(
                f"{self._base_url}/web/search",
                params=params,
            )
        except httpx.TimeoutException:
            logger.warning("Brave 搜索超时：query 长度=%d", len(normalized_query))
            return []
        except httpx.HTTPError as exc:
            logger.warning("Brave 搜索网络异常：%s", type(exc).__name__)
            return []
        except Exception as exc:  # pragma: no cover - 防御性兜底
            logger.warning("Brave 搜索未预期异常：%s", type(exc).__name__)
            return []

        if response.status_code != 200:
            logger.warning(
                "Brave 搜索 HTTP 异常状态：status=%d", response.status_code
            )
            return []

        try:
            payload = response.json()
        except ValueError:
            logger.warning("Brave 搜索响应非 JSON")
            return []

        return self._parse_results(payload, effective_count)

    @staticmethod
    def _parse_results(payload: dict, limit: int) -> list[SearchResult]:
        """从 Brave 响应解析结果；任何结构问题返回 []。"""
        web = payload.get("web") if isinstance(payload, dict) else None
        if not isinstance(web, dict):
            return []
        raw_results = web.get("results")
        if not isinstance(raw_results, list):
            return []

        parsed: list[SearchResult] = []
        for item in raw_results[:limit]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title or not url:
                continue
            description = str(item.get("description") or "").strip()
            parsed.append(SearchResult(title=title, url=url, description=description))
        return parsed

    async def close(self) -> None:
        """释放 client。"""
        if self._client is not None and self._owns_client:
            await self._client.aclose()
        self._client = None

    async def cleanup(self) -> None:
        """兼容 main.py lifespan 的 _cleanup_service 反射调用。"""
        await self.close()
