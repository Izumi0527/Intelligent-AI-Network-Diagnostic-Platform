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

from app.main import create_app
from app.utils.logger import LoggerManager
from app.utils.request_context import reset_request_id, set_request_id


def test_request_id_header_is_passed_through_to_response():
    """客户端传入 X-Request-ID 时，响应头必须透传同一个值。"""
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "trace-client-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "trace-client-123"


def test_request_id_is_generated_when_header_missing():
    """客户端未传 X-Request-ID 时，后端必须生成并返回一个追踪 ID。"""
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get("/api/v1/health")

    request_id = response.headers["X-Request-ID"]
    assert request_id
    assert len(request_id) >= 16


def test_error_payload_uses_same_request_id_as_response_header():
    """错误响应体和响应头必须使用同一个 request_id。"""
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/ai/chat/stream",
            headers={"X-Request-ID": "trace-error-456"},
            json={"model": "", "messages": []},
        )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == "trace-error-456"
    assert response.json()["error"]["request_id"] == "trace-error-456"


def test_application_logs_include_current_request_id(tmp_path):
    """通过统一日志管理器写出的日志必须包含当前 request_id。"""
    token = set_request_id("trace-log-789")
    try:
        manager = LoggerManager(log_base_dir=str(tmp_path))
        logger = manager.get_logger(
            "request_trace_test",
            log_to_file=True,
            log_to_console=False,
        )

        logger.info("终端操作日志")
        for handler in logger.handlers:
            handler.flush()
    finally:
        reset_request_id(token)

    log_file = next((tmp_path / "app").glob("request_trace_test-*.log"))
    content = log_file.read_text(encoding="utf-8")
    assert "trace-log-789" in content
    assert "终端操作日志" in content
