import os
from datetime import datetime, timedelta, timezone

import pytest
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

from app.api.deps import get_terminal_service
from app.core import ssh as ssh_module
from app.core.network.telnet.manager import TelnetManager as NetworkTelnetManager
from app.core.ssh import SSHManager
from app.core.telnet import TelnetManager
from app.core.terminal import TerminalManager
from app.main import app
from app.models.terminal import SessionInfo
from app.utils.security import decrypt_device_password, encrypt_device_password


class FakeTerminalService:
    def __init__(self):
        self.disconnected_session_id = None

    async def disconnect(self, session_id: str):
        self.disconnected_session_id = session_id
        return {"success": True, "message": f"已断开 {session_id}"}


def test_terminal_disconnect_accepts_json_body():
    """断开终端连接应接收前端发送的 JSON body。"""
    fake_service = FakeTerminalService()
    app.dependency_overrides[get_terminal_service] = lambda: fake_service

    try:
        response = TestClient(app).post(
            "/api/v1/terminal/disconnect",
            json={"session_id": "session-1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake_service.disconnected_session_id == "session-1"


@pytest.mark.asyncio
async def test_terminal_cleanup_handles_datetime_last_activity(monkeypatch):
    """闲置清理应使用 datetime 字段计算，不应出现 float 与 datetime 相减。"""
    manager = TerminalManager()
    task = getattr(manager, "session_check_task", None)
    if task:
        task.cancel()

    old_time = datetime.now(timezone.utc) - timedelta(seconds=120)
    manager.sessions["ssh-old"] = SessionInfo(
        session_id="ssh-old",
        connection_type="ssh",
        device_address="127.0.0.1",
        port=22,
        username="admin",
        last_activity=old_time,
    )

    async def fake_disconnect(session_id: str):
        manager.sessions.pop(session_id, None)
        return True, "ok"

    async def fake_ssh_cleanup(idle_timeout: int):
        return 0

    monkeypatch.setattr(manager, "disconnect", fake_disconnect)
    monkeypatch.setattr(manager.ssh_manager, "cleanup_idle_sessions", fake_ssh_cleanup)

    assert await manager.cleanup_idle_sessions(idle_timeout=60) == 1
    assert "ssh-old" not in manager.sessions


@pytest.mark.asyncio
async def test_terminal_manager_does_not_start_session_check_on_init():
    """TerminalManager 构造阶段不应隐式创建后台任务。"""
    manager = TerminalManager()

    assert getattr(manager, "session_check_task", None) is None


@pytest.mark.asyncio
async def test_terminal_manager_background_task_starts_and_stops_explicitly():
    """TerminalManager 后台任务应由应用生命周期显式启动和关闭。"""
    manager = TerminalManager()

    manager.start_background_tasks()
    task = getattr(manager, "session_check_task", None)

    assert task is not None
    assert not task.done()

    await manager.shutdown()
    assert task.cancelled() or task.done()


@pytest.mark.asyncio
async def test_telnet_manager_connect_does_not_start_cleanup_task(monkeypatch):
    """Telnet 连接成功路径不应隐式创建周期清理任务。"""
    manager = NetworkTelnetManager()

    class FakeConnection:
        session_id = "telnet-session"
        last_activity_time = None

        async def connect(self, _timeout: int):
            return True, "ok"

        def is_alive(self):
            return True

        def get_info(self):
            return {"session_id": self.session_id}

        async def disconnect(self):
            return True, "ok"

    monkeypatch.setattr(
        manager,
        "_create_connection",
        lambda *_args, **_kwargs: FakeConnection(),
    )

    success, _, session_id = await manager.connect(
        "192.0.2.10",
        23,
        "admin",
        "password",
    )

    assert success is True
    assert session_id == "telnet-session"
    assert manager._cleanup_task is None


@pytest.mark.asyncio
async def test_ssh_reconnect_keeps_original_public_session_id(monkeypatch):
    """SSH 底层重连后，上层可见的 session_id 必须保持不变。"""
    manager = SSHManager()
    old_session_id = "ssh-old"

    class InactiveShell:
        active = False
        closed = True

    class ActiveShell:
        active = True
        closed = False

        def send(self, _command: str):
            return None

    manager.clients[old_session_id] = {
        "client": object(),
        "shell": InactiveShell(),
        "host": "127.0.0.1",
        "port": 22,
        "username": "admin",
        "password": encrypt_device_password("long-password-for-reconnect"),
        "device_info": "test-device",
        "last_command": "",
        "created_at": 0,
        "last_active": 0,
    }

    async def fake_connect(host, port, username, password, timeout=10):
        manager.clients["ssh-new"] = {
            "client": object(),
            "shell": ActiveShell(),
            "host": host,
            "port": port,
            "username": username,
            "password": encrypt_device_password(password),
            "device_info": "test-device",
            "last_command": "",
            "created_at": 1,
            "last_active": 1,
        }
        return True, "ok", "ssh-new"

    async def fake_receive(_shell):
        return "display version\nOK\n<Huawei>"

    monkeypatch.setattr(manager, "connect", fake_connect)
    monkeypatch.setattr(manager, "_receive_full_output_with_pagination", fake_receive)

    success, output = await manager.execute_command(old_session_id, "display version")

    assert success is True
    assert "OK" in output
    assert old_session_id in manager.clients
    assert "ssh-new" not in manager.clients


def test_device_password_roundtrip_preserves_long_values():
    """设备密码的短期内存保护不能截断超过 32 字节的密码。"""
    password = "p" * 80 + "-复杂密码"

    encrypted = encrypt_device_password(password)

    assert decrypt_device_password(encrypted) == password


def test_ssh_host_key_policy_rejects_unknown_hosts_when_auto_add_disabled(monkeypatch):
    """关闭自动加入主机密钥时，SSH 客户端必须拒绝未知主机。"""
    monkeypatch.setattr(ssh_module.settings, "SSH_AUTO_ADD_HOST_KEY", False)
    manager = SSHManager()

    client = ssh_module.paramiko.SSHClient()
    manager._configure_host_key_policy(client)

    assert isinstance(client._policy, ssh_module.paramiko.RejectPolicy)


@pytest.mark.asyncio
async def test_legacy_telnet_cleanup_returns_integer_count():
    """兼容层的 Telnet 清理接口应返回整数，避免上层累加时报类型错误。"""
    manager = TelnetManager()

    assert await manager.cleanup_idle_sessions(timeout=1) == 0
