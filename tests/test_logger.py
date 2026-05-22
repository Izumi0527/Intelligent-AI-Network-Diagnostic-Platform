import os
import sys

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

from app.utils import logger as logger_module


def test_standard_console_logs_use_color_for_important_levels(monkeypatch, tmp_path):
    """控制台日志应突出重要级别，便于启动时快速识别关键信息。"""
    monkeypatch.setattr(logger_module.settings, "LOG_FORMAT", "standard")
    monkeypatch.setattr(logger_module.settings, "LOG_LEVEL", "INFO")

    class CaptureStream:
        def __init__(self):
            self.content = ""

        def write(self, value):
            self.content += value

        def flush(self):
            pass

    stream = CaptureStream()
    monkeypatch.setattr(sys, "stdout", stream)

    manager = logger_module.LoggerManager(log_base_dir=str(tmp_path))
    logger = manager.get_logger(
        "test_colored_console",
        log_to_file=False,
        log_to_console=True,
    )

    logger.info("启动 AI智能网络故障分析平台 服务")
    logger.warning("警告: 未设置SECRET_KEY，使用默认值可能存在安全风险")
    logger.error("服务器启动失败")

    assert "\033[" in stream.content
    assert "\033[32mINFO\033[0m" in stream.content
    assert "\033[33mWARNING\033[0m" in stream.content
    assert "\033[31mERROR\033[0m" in stream.content


def test_file_logs_remain_plain_text_when_console_is_colored(monkeypatch, tmp_path):
    """文件日志不能写入 ANSI 转义序列，避免影响检索和归档。"""
    monkeypatch.setattr(logger_module.settings, "LOG_FORMAT", "standard")
    monkeypatch.setattr(logger_module.settings, "LOG_LEVEL", "INFO")

    manager = logger_module.LoggerManager(log_base_dir=str(tmp_path))
    logger = manager.get_logger(
        "test_plain_file_logger",
        log_to_file=True,
        log_to_console=False,
    )

    logger.warning("警告: 未设置任何AI服务API密钥，AI功能可能不可用")

    for handler in logger.handlers:
        handler.flush()

    log_file = next((tmp_path / "app").glob("test_plain_file_logger-*.log"))
    content = log_file.read_text(encoding="utf-8")

    assert "\033[" not in content
    assert "WARNING" in content
    assert "AI服务API密钥" in content


def test_standard_formatter_redacts_exception_traceback():
    """标准日志格式化器必须脱敏异常栈中的敏感字段。"""
    formatter = logger_module.SensitiveFormatter("%(message)s\n%(exc_text)s")

    try:
        raise RuntimeError("upstream token=secret-token password=secret")
    except RuntimeError:
        record = logger_module.logging.LogRecord(
            name="security-test",
            level=logger_module.logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="provider failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    formatted = formatter.format(record)

    assert "secret-token" not in formatted
    assert "password=secret" not in formatted
    assert "***" in formatted


def test_formatters_redact_structured_message_values():
    """字符串和 JSON 格式化器都应脱敏 dict/list 形式的结构化日志。"""
    payload = {
        "Authorization": "Bearer secret-token",
        "api_key": "secret-key",
        "messages": [{"content": "敏感提示词"}],
    }
    record = logger_module.logging.LogRecord(
        name="security-test",
        level=logger_module.logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="payload=%s",
        args=(payload,),
        exc_info=None,
    )

    standard = logger_module.SensitiveFormatter("%(message)s").format(record)
    json_text = logger_module.JsonFormatter().format(record)

    for formatted in (standard, json_text):
        assert "secret-token" not in formatted
        assert "secret-key" not in formatted
        assert "敏感提示词" not in formatted
        assert "***" in formatted
