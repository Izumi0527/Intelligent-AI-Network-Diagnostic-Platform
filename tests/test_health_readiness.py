import os

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

from app.api.deps import get_ai_service_manager
from app.config.settings import settings
from app.main import create_app


class ExplodingAIManager:
    async def get_models_response(self):
        raise AssertionError("/health 不应触发 AI 模型检查")


def test_health_is_lightweight_and_does_not_call_ai_manager():
    """轻量 /health 不能触发昂贵或外部 AI 检查。"""
    test_app = create_app()
    test_app.dependency_overrides[get_ai_service_manager] = lambda: ExplodingAIManager()

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["details"]["ai_service"] == "not_checked"


def test_readiness_reports_ready_for_initialized_local_resources():
    """readiness 应检查本地配置和应用资源是否就绪。"""
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        response = client.get("/api/v1/health/ready")

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "ready"
    assert payload["details"]["configuration"] == "ok"
    assert payload["details"]["services"]["terminal_service"] == "available"
    assert payload["details"]["services"]["ai_service_manager"] == "available"
    assert payload["details"]["services"]["rate_limiter"] == "available"


def test_readiness_returns_503_when_required_config_is_missing(monkeypatch):
    """关键配置缺失时 readiness 应返回 503 和统一错误结构。"""
    test_app = create_app()
    monkeypatch.setattr(settings, "PROJECT_NAME", None, raising=False)

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/health/ready",
            headers={"X-Request-ID": "trace-ready-missing"},
        )

    payload = response.json()
    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "trace-ready-missing"
    assert payload["error"]["code"] == "readiness_failed"
    assert payload["error"]["request_id"] == "trace-ready-missing"
    assert payload["error"]["details"][0]["missing_config"] == ["APP_NAME"]
