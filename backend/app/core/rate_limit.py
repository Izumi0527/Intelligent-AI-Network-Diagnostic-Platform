"""可插拔接口限流能力。"""

import math
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.utils.api_errors import api_error_response


@dataclass(frozen=True)
class RateLimitRule:
    """路径级限流规则。"""

    scope: str
    path_prefix: str
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitResult:
    """单次限流判断结果。"""

    allowed: bool
    limit: int
    remaining: int
    reset_after: int


class RateLimiterBackend(Protocol):
    """限流后端协议，后续可替换为 Redis 或网关适配器。"""

    async def hit(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        """记录一次请求并返回限流结果。"""


class InMemoryRateLimiter:
    """基于进程内滑动窗口的限流后端。"""

    def __init__(self):
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def hit(self, key: str, rule: RateLimitRule) -> RateLimitResult:
        now = time.monotonic()
        hits = self._hits[key]
        window_start = now - rule.window_seconds

        while hits and hits[0] <= window_start:
            hits.popleft()

        if len(hits) >= rule.limit:
            return RateLimitResult(
                allowed=False,
                limit=rule.limit,
                remaining=0,
                reset_after=self._reset_after(hits, rule, now),
            )

        hits.append(now)
        return RateLimitResult(
            allowed=True,
            limit=rule.limit,
            remaining=max(0, rule.limit - len(hits)),
            reset_after=self._reset_after(hits, rule, now),
        )

    @staticmethod
    def _reset_after(
        hits: deque[float],
        rule: RateLimitRule,
        now: float,
    ) -> int:
        if not hits:
            return rule.window_seconds
        return max(1, math.ceil(hits[0] + rule.window_seconds - now))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """为指定 API 前缀添加限流判断和响应头。"""

    def __init__(
        self,
        app,
        rules: list[RateLimitRule],
        backend_state_attr: str = "rate_limiter",
    ):
        super().__init__(app)
        self.rules = [rule for rule in rules if rule.limit > 0 and rule.window_seconds > 0]
        self.backend_state_attr = backend_state_attr

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rule = self._match_rule(request.url.path)
        if rule is None:
            return await call_next(request)

        backend = self._get_backend(request)
        result = await backend.hit(self._key_for_request(request, rule), rule)
        headers = self._headers(result)

        if not result.allowed:
            return api_error_response(
                status_code=429,
                code="rate_limit_exceeded",
                message="请求过于频繁，请稍后重试",
                request=request,
                headers={**headers, "Retry-After": str(result.reset_after)},
            )

        response = await call_next(request)
        response.headers.update(headers)
        return response

    def _match_rule(self, path: str) -> RateLimitRule | None:
        for rule in self.rules:
            if path.startswith(rule.path_prefix):
                return rule
        return None

    def _get_backend(self, request: Request) -> RateLimiterBackend:
        backend = getattr(request.app.state, self.backend_state_attr, None)
        if backend is None:
            backend = InMemoryRateLimiter()
            setattr(request.app.state, self.backend_state_attr, backend)
        return backend

    @staticmethod
    def _key_for_request(request: Request, rule: RateLimitRule) -> str:
        client_host = request.client.host if request.client else "unknown"
        return f"{rule.scope}:{client_host}"

    @staticmethod
    def _headers(result: RateLimitResult) -> dict[str, str]:
        return {
            "X-RateLimit-Limit": str(result.limit),
            "X-RateLimit-Remaining": str(result.remaining),
            "X-RateLimit-Reset": str(result.reset_after),
        }
