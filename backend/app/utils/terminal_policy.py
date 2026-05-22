import ipaddress
import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.config.settings import settings


@dataclass
class TerminalPolicyError(ValueError):
    """终端安全策略错误，携带可映射到 HTTP 的状态码。"""

    message: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


def _parse_ip_address(host: str):
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _cidr_contains(ip_address, cidrs: Iterable[str]) -> bool:
    for cidr in cidrs:
        try:
            if ip_address in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError as exc:
            raise TerminalPolicyError(f"终端允许网段配置无效: {cidr}", 500) from exc
    return False


def validate_terminal_target(connection_type: str, device_address: str, port: int) -> None:
    """校验终端连接目标，避免被滥用为敏感地址探测。"""
    host = (device_address or "").strip()
    if not host:
        raise TerminalPolicyError("设备地址不能为空")

    if any(marker in host for marker in ("://", "/", "\\", "@")) or re.search(
        r"\s",
        host,
    ):
        raise TerminalPolicyError("设备地址格式不合法")

    allowed_ports = (
        settings.TERMINAL_ALLOWED_SSH_PORTS
        if connection_type == "ssh"
        else settings.TERMINAL_ALLOWED_TELNET_PORTS
    )
    if port not in allowed_ports:
        raise TerminalPolicyError(f"{connection_type.upper()} 端口不在允许范围内")

    normalized_host = host.lower().rstrip(".")
    allowed_hosts = {item.lower().rstrip(".") for item in settings.TERMINAL_ALLOWED_HOSTS}
    allowed_cidrs = settings.TERMINAL_ALLOWED_CIDRS

    if not allowed_hosts and not allowed_cidrs:
        raise TerminalPolicyError("终端连接必须配置允许主机或允许网段", 403)

    if normalized_host in {"localhost"}:
        raise TerminalPolicyError("不允许连接本机地址", 403)

    ip_address = _parse_ip_address(normalized_host)
    if not ip_address:
        if normalized_host not in allowed_hosts:
            raise TerminalPolicyError("设备域名不在允许列表中", 403)
        return

    if ip_address.is_loopback:
        raise TerminalPolicyError("不允许连接本机地址", 403)
    if ip_address.is_link_local:
        raise TerminalPolicyError("不允许连接链路本地或元数据地址", 403)
    if ip_address.is_unspecified or ip_address.is_multicast:
        raise TerminalPolicyError("不允许连接无效或组播地址", 403)

    host_allowed = normalized_host in allowed_hosts
    cidr_allowed = bool(allowed_cidrs) and _cidr_contains(ip_address, allowed_cidrs)
    if not host_allowed and not cidr_allowed:
        raise TerminalPolicyError("设备地址不在允许网段中", 403)


def validate_terminal_command(command: str) -> str:
    """校验终端命令，默认只放行短小的只读诊断命令。"""
    command_text = (command or "").strip()
    if not command_text:
        raise TerminalPolicyError("命令不能为空")

    if len(command_text) > settings.TERMINAL_COMMAND_MAX_LENGTH:
        raise TerminalPolicyError("命令长度超出限制")

    for pattern in settings.TERMINAL_BLOCKED_COMMAND_PATTERNS:
        if re.search(pattern, command_text, re.IGNORECASE):
            raise TerminalPolicyError("命令包含高风险操作，已拒绝执行")

    for pattern in settings.TERMINAL_ALLOWED_COMMAND_PATTERNS:
        if re.search(pattern, command_text, re.IGNORECASE):
            return command_text

    raise TerminalPolicyError("命令不在只读诊断命令白名单中")
