import os
import warnings

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

from app.api.deps import (
    get_ai_service_manager,
    get_network_service,
    get_terminal_service,
)
from app.config.settings import Settings, settings
from app.utils import logger as logger_utils
from app.main import app, create_app
from app.models.ai import ChatRequest, ChatResponse, Message, ModelsResponse
from app.models.terminal import (
    CommandRequest,
    CommandResponse,
    ConnectionResponse,
    TerminalCredentials,
)
from app.services.ai.base import ProviderType
from app.services.ai.providers.claude_provider import ClaudeProvider
from app.services.ai.providers.deepseek_provider import DeepseekProvider
from app.services.ai.providers.openai_provider import OpenAIProvider
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


class FakeAIManager:
    async def chat(self, request):
        return ChatResponse(
            message=Message(role="assistant", content="ok"),
            model=request.model,
            content="ok",
        )

    async def chat_stream(self, _request):
        yield type("Event", (), {"type": "content", "data": {"content": "ok"}})()
        yield type("Event", (), {"type": "done", "data": {}})()

    async def get_models_response(self):
        return ModelsResponse(models=[], status={})

    async def check_model_status(self, _model_id):
        return True, "ok"


class SensitiveStatusAIManager(FakeAIManager):
    async def check_model_status(self, _model_id):
        return False, "upstream token=secret-token password=secret"


class RejectingTerminalManager:
    def __init__(self):
        self.connect_calls = 0
        self.command_calls = 0

    async def get_all_sessions(self):
        return []

    async def connect(self, **_kwargs):
        self.connect_calls += 1
        return ConnectionResponse(
            success=True,
            session_id="should-not-connect",
            message="不应连接",
        )

    async def execute_command(self, **_kwargs):
        self.command_calls += 1
        return CommandResponse(
            session_id="session-1",
            output="不应执行",
            is_error=False,
        )


def _enable_internal_auth(monkeypatch):
    monkeypatch.setattr(settings, "API_AUTH_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "INTERNAL_API_TOKEN", "test-token", raising=False)


def _auth_headers():
    return {"Authorization": "Bearer test-token"}


def _build_terminal_service(manager):
    service = TerminalService.__new__(TerminalService)
    service.terminal_manager = manager
    service.max_sessions = 5
    service.idle_timeout = 600
    return service


def _set_required_config(monkeypatch):
    required = {
        "API_PREFIX": "/api",
        "APP_NAME": "AI智能网络故障分析平台",
        "APP_VERSION": "0.1.0",
        "SECRET_KEY": "test-secret-key",
        "JWT_ALGORITHM": "HS256",
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        "HOST": "127.0.0.1",
        "PORT": "8000",
        "SESSION_IDLE_TIMEOUT": "600",
        "MAX_TERMINAL_SESSIONS": "5",
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "standard",
        "AI_ENABLED": "false",
    }
    for key, value in required.items():
        monkeypatch.setenv(key, value)


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


def test_ai_chat_requires_internal_token(monkeypatch):
    """AI 对话接口会消耗外部模型能力，缺少内部 Token 时必须拒绝。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app).post(
            "/api/v1/ai/chat",
            json={
                "model": "deepseek-v4-pro",
                "messages": [{"role": "user", "content": "ping"}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_ai_chat_accepts_valid_internal_token(monkeypatch):
    """携带正确内部 Token 时，AI 对话接口应保持原有业务路径。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app).post(
            "/api/v1/ai/chat",
            json={
                "model": "deepseek-v4-pro",
                "messages": [{"role": "user", "content": "ping"}],
            },
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["content"] == "ok"


def test_ai_stream_requires_internal_token(monkeypatch):
    """流式 AI 对话同样必须受内部 Token 保护。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app).post(
            "/api/v1/ai/chat/stream",
            json={
                "model": "deepseek-v4-pro",
                "messages": [{"role": "user", "content": "ping"}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_ai_model_status_requires_internal_token(monkeypatch):
    """模型状态接口不能在未授权场景暴露外部服务连通性。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app).get("/api/v1/ai/models/deepseek-v4-pro/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


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


def test_cors_preflight_rejects_unlisted_headers():
    """凭证模式 CORS 不应镜像任意请求头。"""
    response = TestClient(app).options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Debug-Header",
        },
    )

    assert response.status_code == 400
    assert "x-debug-header" not in response.headers.get(
        "access-control-allow-headers",
        "",
    ).lower()


def test_production_requires_internal_api_auth(monkeypatch):
    """生产环境不能因漏配 API_AUTH_ENABLED 而放开内部接口。"""
    _set_required_config(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "prod-token")

    with pytest.raises(ValueError, match="非 test 环境必须启用内部 API 鉴权"):
        Settings()


def test_production_rejects_placeholder_internal_token(monkeypatch):
    """生产环境必须拒绝示例占位 Token，避免复制模板直接上线。"""
    _set_required_config(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "change-me-internal-api-token")

    with pytest.raises(ValueError, match="INTERNAL_API_TOKEN"):
        Settings()


def test_non_test_environment_rejects_disabled_internal_api_auth(monkeypatch):
    """非 test 环境必须启用内部接口鉴权，不能依赖默认放行。"""
    _set_required_config(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("API_AUTH_ENABLED", "false")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "dev-token")

    with pytest.raises(ValueError, match="非 test 环境必须启用内部 API 鉴权"):
        Settings()


def test_non_test_environment_rejects_missing_internal_api_token(monkeypatch):
    """非 test 环境启用鉴权后必须提供真实内部 Token。"""
    _set_required_config(monkeypatch)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.delenv("INTERNAL_API_TOKEN", raising=False)

    with pytest.raises(ValueError, match="INTERNAL_API_TOKEN"):
        Settings()


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


def test_production_disables_api_documentation(monkeypatch):
    """production 环境必须关闭 API 文档和 OpenAPI 枚举入口。"""
    monkeypatch.setattr(settings, "APP_ENV", "production")
    production_app = create_app()
    client = TestClient(production_app, raise_server_exceptions=False)

    for path in (
        f"{settings.API_V1_STR}/docs",
        f"{settings.API_V1_STR}/redoc",
        f"{settings.API_V1_STR}/openapi.json",
    ):
        response = client.get(path)
        assert response.status_code == 404


def test_create_app_uses_lifespan_without_on_event_deprecation(monkeypatch):
    """应用启动/关闭逻辑应使用 lifespan，避免继续注册 on_event。"""
    monkeypatch.setattr(settings, "APP_ENV", "test")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always", DeprecationWarning)
        create_app()

    assert not any("on_event is deprecated" in str(item.message) for item in captured)


def test_deepseek_generate_requires_internal_token(monkeypatch):
    """Deepseek 生成接口属于受保护能力，缺少 Token 应直接返回 401。"""
    _enable_internal_auth(monkeypatch)

    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/ai/deepseek/generate",
        json={"messages": [{"role": "user", "content": "ping"}]},
    )

    assert response.status_code == 401


def test_ai_chat_rejects_oversized_message_content(monkeypatch):
    """AI 对话必须拒绝超长单条消息，避免成本放大和请求体滥用。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/ai/chat",
            json={
                "model": "deepseek-v4-pro",
                "messages": [{"role": "user", "content": "x" * 8001}],
            },
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_ai_chat_rejects_invalid_sampling_parameters(monkeypatch):
    """AI 对话必须限制 max_tokens、temperature 和 top_p 的安全范围。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/ai/chat",
            json={
                "model": "deepseek-v4-pro",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 100000,
                "temperature": 3,
                "top_p": 2,
            },
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_ai_chat_rejects_too_many_messages(monkeypatch):
    """AI 对话必须限制消息数量，避免批量请求放大资源消耗。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/ai/chat",
            json={
                "model": "deepseek-v4-pro",
                "messages": [
                    {"role": "user", "content": f"ping-{index}"}
                    for index in range(51)
                ],
            },
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_ai_chat_rejects_total_message_content_over_limit(monkeypatch):
    """AI 对话必须限制消息总长度，避免拆分多条绕过单条长度限制。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/ai/chat",
            json={
                "model": "deepseek-v4-pro",
                "messages": [
                    {"role": "user", "content": "x" * 8000}
                    for _ in range(5)
                ],
            },
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_deepseek_generate_rejects_oversized_message(monkeypatch):
    """Deepseek 兼容生成接口应复用 AI 请求边界约束。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/ai/deepseek/generate",
            json={
                "messages": [{"role": "user", "content": "x" * 8001}],
                "max_tokens": 2048,
            },
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_deepseek_generate_rejects_invalid_sampling_parameters(monkeypatch):
    """Deepseek 兼容生成接口应限制采样参数和 max_tokens。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: FakeAIManager()

    try:
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/ai/deepseek/generate",
            json={
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 100000,
                "temperature": 3,
                "top_p": 2,
            },
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_ai_status_endpoint_does_not_expose_upstream_error_detail(monkeypatch):
    """模型连接状态接口不能把上游错误详情透传给客户端。"""
    _enable_internal_auth(monkeypatch)
    app.dependency_overrides[get_ai_service_manager] = lambda: SensitiveStatusAIManager()

    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/v1/ai/models/deepseek-v4-pro/status",
            headers=_auth_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["message"] == "AI 服务暂时不可用，请稍后重试"
    assert "secret-token" not in response.text
    assert "password=secret" not in response.text


def test_ai_provider_payload_uses_safe_defaults_and_top_p():
    """provider 请求体不能向上游发送 None 参数，且应透传已校验的 top_p。"""
    request = ChatRequest(
        model="deepseek-v4-pro",
        messages=[Message(role="user", content="ping")],
        top_p=0.8,
    )
    providers = [
        OpenAIProvider("test-key"),
        DeepseekProvider("test-key"),
        ClaudeProvider("test-key"),
    ]

    payloads = [
        providers[0]._build_chat_payload(request),
        providers[1]._build_deepseek_payload(request),
        providers[2]._build_claude_payload(request),
    ]

    for payload in payloads:
        assert payload["max_tokens"] is not None
        assert payload["temperature"] is not None
        assert payload["top_p"] == 0.8


def test_ai_provider_error_response_does_not_expose_upstream_detail():
    """AI provider 返回给客户端的错误不能包含上游原文敏感信息。"""
    provider = OpenAIProvider("test-key")
    request = ChatRequest(
        model="gpt-test",
        messages=[Message(role="user", content="ping")],
    )

    response = provider._error_chat_response(
        request,
        'upstream failed token=secret-token https://proxy.example.com/account',
    )

    assert response.usage["error"] is True
    assert response.usage["provider"] == ProviderType.OPENAI.value
    assert response.id == response.usage["request_id"]
    assert response.message.content == "AI 服务暂时不可用，请稍后重试"
    assert "secret-token" not in response.message.content
    assert "proxy.example.com" not in response.message.content

    event = provider._error_stream_event(
        'upstream failed token=secret-token https://proxy.example.com/account',
    )
    assert event.type == "error"
    assert event.data["request_id"]
    assert event.data["error"] == "AI 服务暂时不可用，请稍后重试"
    assert "secret-token" not in event.data["error"]


@pytest.mark.asyncio
async def test_terminal_service_rejects_loopback_target_before_network():
    """终端连接不能被滥用为本机或内网敏感地址探测。"""
    manager = RejectingTerminalManager()
    service = _build_terminal_service(manager)

    with pytest.raises(HTTPException) as exc_info:
        await service.connect(
            TerminalCredentials(
                connection_type="ssh",
                device_address="127.0.0.1",
                port=22,
                username="admin",
                password="password",
            )
        )

    assert exc_info.value.status_code in {400, 403}
    assert manager.connect_calls == 0


@pytest.mark.asyncio
async def test_terminal_service_rejects_metadata_target_before_network():
    """终端连接必须拒绝云元数据地址。"""
    manager = RejectingTerminalManager()
    service = _build_terminal_service(manager)

    with pytest.raises(HTTPException) as exc_info:
        await service.connect(
            TerminalCredentials(
                connection_type="ssh",
                device_address="169.254.169.254",
                port=22,
                username="admin",
                password="password",
            )
        )

    assert exc_info.value.status_code in {400, 403}
    assert manager.connect_calls == 0


@pytest.mark.asyncio
async def test_terminal_service_rejects_unapproved_ssh_port_before_network():
    """SSH 连接只能使用配置允许的端口。"""
    manager = RejectingTerminalManager()
    service = _build_terminal_service(manager)

    with pytest.raises(HTTPException) as exc_info:
        await service.connect(
            TerminalCredentials(
                connection_type="ssh",
                device_address="192.0.2.10",
                port=22222,
                username="admin",
                password="password",
            )
        )

    assert exc_info.value.status_code == 400
    assert manager.connect_calls == 0


@pytest.mark.asyncio
async def test_terminal_service_requires_target_allowlist_before_network(monkeypatch):
    """未配置终端允许主机或网段时，必须 fail-closed 拒绝连接。"""
    monkeypatch.setattr(settings, "TERMINAL_ALLOWED_HOSTS", [], raising=False)
    monkeypatch.setattr(settings, "TERMINAL_ALLOWED_CIDRS", [], raising=False)
    manager = RejectingTerminalManager()
    service = _build_terminal_service(manager)

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

    assert exc_info.value.status_code == 403
    assert manager.connect_calls == 0


@pytest.mark.asyncio
async def test_terminal_service_allows_configured_target_cidr(monkeypatch):
    """配置命中允许网段时，应继续进入正式连接路径。"""
    monkeypatch.setattr(settings, "TERMINAL_ALLOWED_HOSTS", [], raising=False)
    monkeypatch.setattr(settings, "TERMINAL_ALLOWED_CIDRS", ["192.0.2.0/24"], raising=False)
    manager = RejectingTerminalManager()
    service = _build_terminal_service(manager)

    response = await service.connect(
        TerminalCredentials(
            connection_type="ssh",
            device_address="192.0.2.10",
            port=22,
            username="admin",
            password="password",
        )
    )

    assert response.success is True
    assert manager.connect_calls == 1


@pytest.mark.asyncio
async def test_terminal_service_rejects_dangerous_command_before_shell():
    """破坏性设备命令必须在写入 SSH/Telnet shell 前被拒绝。"""
    manager = RejectingTerminalManager()
    service = _build_terminal_service(manager)

    with pytest.raises(HTTPException) as exc_info:
        await service.execute_command(
            CommandRequest(session_id="session-1", command="reboot")
        )

    assert exc_info.value.status_code == 400
    assert manager.command_calls == 0


@pytest.mark.asyncio
async def test_terminal_service_allows_readonly_diagnostic_command():
    """只读诊断命令应被允许进入终端执行路径。"""
    manager = RejectingTerminalManager()
    service = _build_terminal_service(manager)

    response = await service.execute_command(
        CommandRequest(session_id="session-1", command="display version")
    )

    assert response.is_error is False
    assert manager.command_calls == 1


@pytest.mark.asyncio
async def test_terminal_service_rejects_sensitive_configuration_read_before_shell():
    """读取完整配置等敏感命令必须在写入 shell 前被拒绝。"""
    manager = RejectingTerminalManager()
    service = _build_terminal_service(manager)

    with pytest.raises(HTTPException) as exc_info:
        await service.execute_command(
            CommandRequest(session_id="session-1", command="display current-configuration")
        )

    assert exc_info.value.status_code == 400
    assert manager.command_calls == 0


def test_sensitive_log_redaction_removes_tokens_passwords_and_content():
    """日志脱敏工具不能留下 Token、密码或大段内容明文。"""
    redact = getattr(logger_utils, "redact_sensitive_text", None)

    assert callable(redact)
    redacted = redact(
        "Authorization: Bearer secret-token password=secret content=业务敏感内容"
    )

    assert "secret-token" not in redacted
    assert "password=secret" not in redacted
    assert "业务敏感内容" not in redacted
    assert "***" in redacted


def test_json_formatter_redacts_sensitive_message_fields():
    """JSON 日志格式化器必须全局脱敏普通 logger 消息。"""
    record = logger_utils.logging.LogRecord(
        name="security-test",
        level=logger_utils.logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Authorization: Bearer secret-token password=secret content=敏感提示词",
        args=(),
        exc_info=None,
    )

    formatted = logger_utils.JsonFormatter().format(record)

    assert "secret-token" not in formatted
    assert "password=secret" not in formatted
    assert "敏感提示词" not in formatted
    assert "***" in formatted


def test_standard_formatter_redacts_sensitive_message_fields():
    """标准日志格式化器同样必须在 formatter 层脱敏。"""
    formatter = logger_utils.SensitiveFormatter("%(message)s")
    record = logger_utils.logging.LogRecord(
        name="security-test",
        level=logger_utils.logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="api_key=secret-key content=敏感输出",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)

    assert "secret-key" not in formatted
    assert "敏感输出" not in formatted
    assert "***" in formatted


@pytest.mark.asyncio
async def test_terminal_service_uses_generic_500_message(monkeypatch):
    """终端服务内部异常不能把底层敏感错误直接暴露给用户。"""
    monkeypatch.setattr(settings, "TERMINAL_ALLOWED_HOSTS", [], raising=False)
    monkeypatch.setattr(settings, "TERMINAL_ALLOWED_CIDRS", ["192.0.2.0/24"], raising=False)
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
