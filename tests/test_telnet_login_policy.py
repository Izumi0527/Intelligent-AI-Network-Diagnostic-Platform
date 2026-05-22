import os
import re
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

from app.core.network.telnet import connection as telnet_connection_module
from app.core.network.telnet.connection import TelnetConnection
from app.core.network.telnet.devices import huawei as huawei_module
from app.core.network.telnet.devices.huawei import HuaweiTelnetConnection


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeSocket:
    def settimeout(self, _timeout):
        return None

    def connect(self, _address):
        return None


class ScriptedTelnetClient:
    def __init__(self, *, read_until_responses=None, eager_responses=None, expect_responses=None):
        self.read_until_responses = list(read_until_responses or [])
        self.eager_responses = list(eager_responses or [])
        self.expect_responses = list(expect_responses or [])
        self.writes = []
        self.sock = None

    def open(self, *_args):
        return None

    def read_until(self, *_args):
        if self.read_until_responses:
            return self.read_until_responses.pop(0)
        return b""

    def read_very_eager(self):
        if self.eager_responses:
            return self.eager_responses.pop(0)
        return b""

    def expect(self, patterns, _timeout):
        data = self.expect_responses.pop(0)
        for index, pattern in enumerate(patterns):
            if hasattr(pattern, "search"):
                match = pattern.search(data)
            else:
                match = re.search(pattern, data, re.IGNORECASE)
            if match:
                return index, match, data
        return -1, None, data

    def write(self, data):
        self.writes.append(data)


def test_telnet_login_accepts_login_prompt_and_utf8_credentials(monkeypatch):
    """Telnet 登录应识别 Login/Password 提示，并用 UTF-8 发送凭据。"""
    fake_client = ScriptedTelnetClient(
        read_until_responses=[b"Login:", b"Password:"],
        eager_responses=[b"Welcome", b"<Huawei>"],
        expect_responses=[b"Login:", b"Password:", b"<Huawei>"],
    )
    monkeypatch.setattr(telnet_connection_module, "TelnetClient", lambda: fake_client)
    monkeypatch.setattr(telnet_connection_module.time, "sleep", lambda _seconds: None)

    connection = TelnetConnection("192.0.2.10", 23, "管理员", "复杂密码")
    monkeypatch.setattr(connection, "_check_host_reachable", lambda _timeout: True)

    success, message = connection._connect_sync(timeout=1)

    assert success is True, message
    assert "管理员".encode("utf-8") + b"\n" in fake_client.writes
    assert "复杂密码".encode("utf-8") + b"\n" in fake_client.writes


def test_huawei_telnet_does_not_enter_system_view_after_login(monkeypatch):
    """华为 Telnet 登录成功后应停留在用户视图，不自动执行 system-view。"""
    fake_client = ScriptedTelnetClient(
        read_until_responses=[b"Username:", b"Password:", b"<Huawei>"],
        expect_responses=[b"Username:", b"Password:", b"<Huawei>"],
    )
    monkeypatch.setattr(huawei_module.socket, "socket", lambda *_args: FakeSocket())
    monkeypatch.setattr(huawei_module, "TelnetClient", lambda sock=None: fake_client)

    connection = HuaweiTelnetConnection("192.0.2.10", 23, "admin", "password")

    success, message = connection._huawei_direct_connect(timeout=1)

    assert success is True, message
    assert not any(b"system-view" in item for item in fake_client.writes)


def test_telnet_completion_ignores_pagination_prompt_and_detects_device_prompt():
    """分页提示不能误判命令结束，完整响应末尾的设备提示符应判定完成。"""
    connection = TelnetConnection("192.0.2.10", 23, "admin", "password")

    assert connection._check_command_completion(
        b"<--- More --->",
        b"display current-configuration\n<--- More --->",
    ) is False
    assert connection._check_command_completion(
        b"",
        b"display version\nVersion info\n<Huawei>",
    ) is True


def test_telnet_runtime_no_longer_imports_stdlib_telnetlib():
    """运行时代码不应再导入 Python 3.13 移除的 telnetlib。"""
    telnet_files = [
        PROJECT_ROOT / "backend/app/core/network/telnet/connection.py",
        PROJECT_ROOT / "backend/app/core/network/telnet/devices/huawei.py",
    ]

    for path in telnet_files:
        assert "telnetlib" not in path.read_text(encoding="utf-8")
