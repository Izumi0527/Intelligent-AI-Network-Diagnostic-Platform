import os

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("API_PREFIX", "/api")
os.environ.setdefault("APP_NAME", "AI智能网络故障分析平台")
os.environ.setdefault("APP_VERSION", "0.1.0")
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

from app.api.deps import get_network_service, get_terminal_service
from app.config.settings import Settings, settings
from app.main import app
from app.models.terminal import ConnectionResponse, TerminalCredentials
from app.services.terminal_service import TerminalService


class FakeTerminalConnectService:
    def __init__(self):
        self.connect_calls = 0

    async def connect(self, credentials: TerminalCredentials):
        self.connect_calls += 1
        return ConnectionResponse(
            success=True,
            session_id="terminal-test",
            message=f"已连接 {credentials.device_address}",
        )


class FailingNetworkService:
    async def connect(self, _request):
        raise AssertionError("废弃 /network/connect 不应调用 NetworkService")

    async def get_connections(self):
        raise AssertionError("健康检查不应依赖 NetworkService 连接统计")


class BrokenTerminalManager:
    async def get_all_sessions(self):
        return []

    async def connect(self, **_kwargs):
        raise RuntimeError("sensitive device stack trace")


def _enable_internal_auth(monkeypatch):
    monkeypatch.setattr(settings, "API_AUTH_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "test-token", raising=False)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def test_terminal_connect_requires_internal_token(monkeypatch):
    """受保护的终端连接接口缺少内部 Token 时应拒绝访问。"""
    _enable_internal_auth(monkeypatch)
    fake_service = FakeTerminalConnectService()
    app.dependency_overrides[get_terminal_service] = lambda: fake_service

    try:
        response = TestClient(app).post(
            "/api/v1/terminal/connect",
            json={
                "connection_type": "ssh",
                "device_address": "192.0.2.10",
                "port": 22,
                "username": "admin",
                "password": "password",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert fake_service.connect_calls == 0


def test_terminal_connect_accepts_valid_internal_token(monkeypatch):
    """携带正确内部 Token 时，终端连接接口应继续走正式服务路径。"""
    _enable_internal_auth(monkeypatch)
    fake_service = FakeTerminalConnectService()
    app.dependency_overrides[get_terminal_service] = lambda: fake_service

    try:
        response = TestClient(app).post(
            "/api/v1/terminal/connect",
            json={
                "connection_type": "ssh",
                "device_address": "192.0.2.10",
                "port": 22,
                "username": "admin",
                "password": "password",
            },
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake_service.connect_calls == 1


def test_network_connect_is_gone_and_does_not_call_legacy_service(monkeypatch):
    """废弃的 /network 写接口应返回 410，并停止承载旧连接能力。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_network_service] = lambda: FailingNetworkService()

    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/network/connect",
            json={
                "host": "192.0.2.10",
                "port": 22,
                "username": "admin",
                "password": "password",
                "connection_type": "SSH",
                "device_type": "cisco_ios",
            },
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 410
    assert "/terminal" in response.text


def test_health_does_not_depend_on_network_service(monkeypatch):
    """健康检查不应为了统计旧连接而初始化废弃 NetworkService。"""
    app.dependency_overrides[get_network_service] = lambda: FailingNetworkService()

    try:
        response = TestClient(app, raise_server_exceptions=False).get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_cors_origins_remove_wildcard_and_empty_items(monkeypatch):
    """开启凭证模式时，CORS 示例与解析结果都不能保留通配 origin。"""
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "http://localhost:5173, *, http://localhost:5174,,",
    )

    parsed = Settings()

    assert parsed.BACKEND_CORS_ORIGINS == [
        "http://localhost:5173",
        "http://localhost:5174",
    ]


def test_debug_request_format_hidden_outside_development(monkeypatch):
    """调试回显接口只能在 development 环境且通过鉴权后访问。"""
    _enable_internal_auth(monkeypatch)
    monkeypatch.setattr(settings, "APP_ENV", "production")

    response = TestClient(app).post(
        "/api/v1/ai/debug/request-format",
        json={"messages": []},
        headers=_auth_headers(),
    )

    assert response.status_code in {403, 404}


def test_deepseek_generate_requires_internal_token(monkeypatch):
    """Deepseek 生成接口属于受保护能力，缺少 Token 应直接返回 401。"""
    _enable_internal_auth(monkeypatch)

    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/ai/deepseek/generate",
        json={"messages": [{"role": "user", "content": "ping"}]},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_terminal_service_uses_generic_500_message():
    """终端服务内部异常不能把底层敏感错误直接暴露给用户。"""
    service = TerminalService.__new__(TerminalService)
    service.terminal_manager = BrokenTerminalManager()
    service.max_sessions = 5
    service.idle_timeout = 600

    with pytest.raises(HTTPException) as exc_info:
        await service.connect(
            TerminalCredentials(
                connection_type="ssh",
                device_address="192.0.2.10",
                port=22,
                username="admin",
                password="password",
            )
        )

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "内部服务器错误"
    assert "sensitive" not in exc_info.value.detail
