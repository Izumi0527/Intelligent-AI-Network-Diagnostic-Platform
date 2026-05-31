import os

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("API_PREFIX", "/api")
os.environ.setdefault("APP_NAME", "AI智能网络故障分析平台")
os.environ.setdefault("APP_VERSION", "0.2.1")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("HOST", "127.0.0.1")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("SESSION_IDLE_TIMEOUT", "600")
os.environ.setdefault("MAX_TERMINAL_SESSIONS", "5")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("LOG_FORMAT", "standard")
os.environ.setdefault("AI_ENABLED", "false")

from app.api.deps import get_ai_application_service, get_terminal_service
from app.config.settings import settings
from app.core.rate_limit import RateLimitResult
from app.main import create_app
from app.services.ai.application_service import AIApplicationError
from app.services.terminal_exceptions import SessionNotFound


class FailingAIApplicationService:
    def chat_stream(self, _request):
        raise AIApplicationError("AI 服务暂时不可用，请稍后重试", status_code=502)


class MissingSessionTerminalService:
    async def get_session(self, session_id: str):
        raise SessionNotFound(f"会话不存在: {session_id}")


class StaticRateLimiter:
    async def hit(self, _key, _rule):
        return RateLimitResult(
            allowed=False,
            limit=1,
            remaining=0,
            reset_after=30,
        )


def test_validation_error_uses_standard_api_error_shape():
    """FastAPI validation 错误必须使用统一 error 包装。"""
    response = TestClient(create_app(), raise_server_exceptions=False).post(
        "/api/v1/ai/chat/stream",
        json={"model": "", "messages": []},
    )

    payload = response.json()
    assert response.status_code == 422
    assert set(payload) == {"error"}
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "请求参数验证失败"
    assert payload["error"]["request_id"]
    assert isinstance(payload["error"]["details"], list)
    assert payload["error"]["details"]


def test_auth_error_uses_standard_api_error_shape(monkeypatch):
    """内部鉴权失败必须使用统一 error 包装并保留 WWW-Authenticate。"""
    monkeypatch.setattr(settings, "API_AUTH_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "test-token", raising=False)

    response = TestClient(create_app(), raise_server_exceptions=False).get(
        "/api/v1/ai/models",
    )

    payload = response.json()
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert payload["error"]["code"] == "unauthorized"
    assert payload["error"]["message"] == "未授权"
    assert payload["error"]["request_id"]
    assert payload["error"]["details"] == []


def test_rate_limit_error_uses_standard_api_error_shape():
    """限流错误也必须使用统一 error 包装并保留限流响应头。"""
    test_app = create_app()

    with TestClient(test_app, raise_server_exceptions=False) as client:
        test_app.state.rate_limiter = StaticRateLimiter()
        response = client.post(
            "/api/v1/ai/chat/stream",
            json={
                "model": "deepseek-v4-pro",
                "messages": [{"role": "user", "content": "ping"}],
            },
        )

    payload = response.json()
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"
    assert payload["error"]["code"] == "rate_limit_exceeded"
    assert payload["error"]["message"] == "请求过于频繁，请稍后重试"
    assert payload["error"]["request_id"]
    assert payload["error"]["details"] == []


def test_business_error_uses_standard_api_error_shape():
    """业务异常经路由映射后必须使用统一 error 包装。"""
    test_app = create_app()
    test_app.dependency_overrides[get_terminal_service] = (
        lambda: MissingSessionTerminalService()
    )

    response = TestClient(test_app, raise_server_exceptions=False).get(
        "/api/v1/terminal/sessions/session-missing",
    )

    payload = response.json()
    assert response.status_code == 404
    assert payload["error"]["code"] == "not_found"
    assert payload["error"]["message"] == "会话不存在: session-missing"
    assert payload["error"]["request_id"]
    assert payload["error"]["details"] == []


def test_upstream_error_uses_standard_api_error_shape():
    """上游 AI 异常必须使用统一 error 包装，且不暴露内部细节。"""
    test_app = create_app()
    test_app.dependency_overrides[get_ai_application_service] = (
        lambda: FailingAIApplicationService()
    )

    response = TestClient(test_app, raise_server_exceptions=False).post(
        "/api/v1/ai/chat/stream",
        json={
            "model": "deepseek-v4-pro",
            "messages": [{"role": "user", "content": "ping"}],
        },
    )

    payload = response.json()
    assert response.status_code == 502
    assert payload["error"]["code"] == "upstream_error"
    assert payload["error"]["message"] == "AI 服务暂时不可用，请稍后重试"
    assert payload["error"]["request_id"]
    assert payload["error"]["details"] == []
