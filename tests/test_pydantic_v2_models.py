import os
import subprocess
import sys
import textwrap


def test_ai_and_terminal_models_do_not_emit_pydantic_v1_deprecation_warnings():
    """AI 与终端模型应使用 Pydantic v2 写法，不再触发 v1 弃用警告。"""
    env = os.environ.copy()
    env.setdefault("APP_ENV", "test")
    code = textwrap.dedent(
        """
        import warnings

        from pydantic.warnings import PydanticDeprecatedSince20

        warnings.simplefilter("error", PydanticDeprecatedSince20)

        from app.models.ai import ChatRequest, DeepseekGenerateRequest, Message
        from app.models.terminal import (
            CommandResponse,
            SessionInfo,
            TerminalCredentials,
        )

        message = Message(role="user", content=" ping ")
        assert message.content == "ping"
        ChatRequest(model="deepseek-v4-pro", messages=[message])
        DeepseekGenerateRequest(messages=[message])
        TerminalCredentials(
            connection_type="ssh",
            device_address="192.0.2.10",
            port=22,
            username="admin",
            password="password",
        )
        CommandResponse(session_id="s1", output="ok")
        SessionInfo(
            session_id="s1",
            connection_type="ssh",
            device_address="192.0.2.10",
            port=22,
            username="admin",
        )
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
