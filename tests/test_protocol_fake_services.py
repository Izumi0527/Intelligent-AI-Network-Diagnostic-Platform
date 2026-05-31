import os

import pytest

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

from protocol_fakes import (
    DisconnectingTelnetClient,
    ScriptedAIManager,
    ScriptedShell,
)

from app.core.network.base import ConnectionStatus
from app.core.network.telnet.connection import TelnetConnection
from app.core.ssh import SSHManager
from app.models.ai import ChatRequest, Message
from app.services.ai.application_service import AIApplicationService


@pytest.mark.asyncio
async def test_fake_ssh_shell_drives_pagination_without_real_device(monkeypatch):
    """fake SSH shell 应覆盖分页读取，且不依赖真实网络设备。"""
    manager = SSHManager()
    shell = ScriptedShell(
        recv_chunks=[
            b"display version\r\nVersion page 1\r\n---- More ----",
            b"Version page 2\r\n<Huawei>",
        ],
        recv_ready_values=[False],
    )
    monkeypatch.setattr("app.core.ssh.asyncio.sleep", _async_noop)

    output = await manager._receive_full_output_with_pagination(shell)

    assert "Version page 1" in output
    assert "Version page 2" in output
    assert b" " in shell.sent_data


def test_fake_telnet_client_drives_disconnect_error_without_real_socket():
    """fake Telnet 客户端应覆盖断连异常，且不创建真实 socket。"""
    connection = TelnetConnection("192.0.2.10", 23, "admin", "password")
    connection.status = ConnectionStatus.CONNECTED
    connection.client = DisconnectingTelnetClient()

    success, message = connection._execute_command_sync("display version")

    assert success is False
    assert "连接被远端断开" in message
    assert b"display version\n" in connection.client.writes


@pytest.mark.asyncio
async def test_fake_ai_provider_drives_stream_error_without_upstream_call():
    """fake AI provider 应覆盖流式中途失败，并保持 SSE 错误结构。"""
    ai_manager = ScriptedAIManager(
        stream_events=[
            ("content", {"content": "hello"}),
            RuntimeError("upstream token=secret-token stream dropped"),
        ]
    )
    service = AIApplicationService(ai_manager)
    request = ChatRequest(
        model="deepseek-v4-pro",
        messages=[Message(role="user", content="ping")],
        stream=True,
    )

    chunks = [chunk async for chunk in service.chat_stream(request).chunks]

    assert chunks[0].startswith("event: content\n")
    assert chunks[-1].startswith("event: error\n")
    assert "secret-token" not in chunks[-1]
    assert ai_manager.stream_calls == 1


async def _async_noop(_seconds):
    return None
