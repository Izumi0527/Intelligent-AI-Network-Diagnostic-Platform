import asyncio
import os
from pathlib import Path

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

from app.services.ai.providers.deepseek_provider import DeepseekProvider
from app.utils.model_config import ModelConfigParser


EXPECTED_ENV_MODELS = {
    "OPENAI_MODELS": ["gpt-5.5", "gpt-5.4-mini"],
    "CLAUDE_MODELS": [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
    ],
    "DEEPSEEK_MODELS": ["deepseek-v4-pro", "deepseek-v4-flash"],
}


def _read_env_example() -> dict[str, str]:
    env_path = Path(__file__).resolve().parents[1] / "backend" / ".env.example"
    values = {}

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.split("  #", 1)[0].strip()

    return values


def _split_env_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def test_env_example_uses_latest_supported_models():
    """示例配置应使用当前三家厂商的先进可用模型。"""
    values = _read_env_example()

    for key, expected_models in EXPECTED_ENV_MODELS.items():
        assert _split_env_list(values[key]) == expected_models

    assert values["CLAUDE_MODEL_VERSION"] == "claude-opus-4-7"
    assert values["DEEPSEEK_MODEL_VERSION"] == "deepseek-v4-pro"


def test_builtin_default_models_are_current_when_parser_falls_back():
    """解析异常时的内置兜底也不能回退到已过时模型。"""
    openai_models = ModelConfigParser._get_default_openai_models()
    claude_models = ModelConfigParser._get_default_claude_models()
    deepseek_models = ModelConfigParser._get_default_deepseek_models()

    assert [model.value for model in openai_models] == ["gpt-5.5", "gpt-5.4-mini"]
    assert [model.value for model in claude_models] == [
        "claude-opus-4-7",
        "claude-sonnet-4-6",
        "claude-haiku-4-5",
    ]
    assert [model.value for model in deepseek_models] == [
        "deepseek-v4-pro",
        "deepseek-v4-flash",
    ]


def test_deepseek_connection_check_uses_first_configured_model(monkeypatch):
    """DeepSeek 连接检查应避开即将退役的旧模型别名。"""
    monkeypatch.setenv("DEEPSEEK_MODELS", "deepseek-v4-pro,deepseek-v4-flash")
    monkeypatch.setenv("DEEPSEEK_MODEL_NAMES", "DeepSeek-V4-Pro,DeepSeek-V4-Flash")
    monkeypatch.setenv("DEEPSEEK_MODEL_DESCRIPTIONS", "旗舰推理与智能体模型,快速经济模型")
    monkeypatch.setenv("DEEPSEEK_MODEL_MAX_TOKENS", "1000000,1000000")

    posted_payloads = []

    class FakeResponse:
        status_code = 200
        text = "{}"

    class FakeClient:
        async def post(self, url, json):
            posted_payloads.append(json)
            return FakeResponse()

    provider = DeepseekProvider("test-key")

    async def fake_initialize():
        provider.client = FakeClient()

    monkeypatch.setattr(provider, "initialize", fake_initialize)

    is_connected, _ = asyncio.run(provider.check_connection())

    assert is_connected is True
    assert posted_payloads[0]["model"] == "deepseek-v4-pro"
