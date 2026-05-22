"""最小 Telnet 客户端，替代 Python 3.13 已移除的标准库实现。"""

import re
import socket
import time

IAC = 255
SE = 240
WILL = 251
WONT = 252
DO = 253
DONT = 254
SB = 250


class TelnetClient:
    """兼容项目现有调用面的同步 Telnet 客户端。"""

    def __init__(self, sock: socket.socket | None = None):
        self.sock = sock

    def open(self, host: str, port: int, timeout: float | None = None) -> None:
        self.sock = socket.create_connection((host, port), timeout=timeout)

    def write(self, data: bytes) -> None:
        if not self.sock:
            raise ConnectionError("Telnet socket is not connected")
        self.sock.sendall(data)

    def read_until(self, expected: bytes, timeout: float | None = None) -> bytes:
        deadline = self._deadline(timeout)
        data = b""

        while expected not in data:
            chunk = self._recv_once(deadline)
            if not chunk:
                break
            data += chunk

        return data

    def read_very_eager(self) -> bytes:
        if not self.sock:
            return b""

        original_timeout = self.sock.gettimeout()
        chunks = []
        try:
            self.sock.settimeout(0)
            while True:
                try:
                    chunk = self.sock.recv(4096)
                except (BlockingIOError, socket.timeout):
                    break
                if not chunk:
                    break
                chunks.append(self._strip_telnet_commands(chunk))
        finally:
            self.sock.settimeout(original_timeout)

        return b"".join(chunks)

    def expect(
        self,
        patterns: list[re.Pattern[bytes] | bytes],
        timeout: float | None = None,
    ) -> tuple[int, re.Match[bytes] | None, bytes]:
        deadline = self._deadline(timeout)
        data = b""

        while True:
            for index, pattern in enumerate(patterns):
                match = (
                    pattern.search(data)
                    if hasattr(pattern, "search")
                    else re.search(pattern, data)
                )
                if match:
                    return index, match, data

            chunk = self._recv_once(deadline)
            if not chunk:
                return -1, None, data
            data += chunk

    def close(self) -> None:
        if self.sock:
            self.sock.close()
            self.sock = None

    def _recv_once(self, deadline: float | None) -> bytes:
        if not self.sock:
            return b""

        timeout = None if deadline is None else max(0, deadline - time.monotonic())
        self.sock.settimeout(timeout)
        try:
            chunk = self.sock.recv(4096)
        except socket.timeout:
            return b""
        if not chunk:
            return b""
        return self._strip_telnet_commands(chunk)

    @staticmethod
    def _deadline(timeout: float | None) -> float | None:
        if timeout is None:
            return None
        return time.monotonic() + timeout

    def _strip_telnet_commands(self, data: bytes) -> bytes:
        """过滤 Telnet IAC 协商，并对远端选项请求做保守拒绝。"""
        if IAC not in data:
            return data

        output = bytearray()
        index = 0
        while index < len(data):
            byte = data[index]
            if byte != IAC:
                output.append(byte)
                index += 1
                continue

            if index + 1 >= len(data):
                break

            command = data[index + 1]
            if command == IAC:
                output.append(IAC)
                index += 2
                continue

            if command == SB:
                index = self._skip_subnegotiation(data, index + 2)
                continue

            if command in {DO, DONT, WILL, WONT} and index + 2 < len(data):
                option = data[index + 2]
                if command == DO:
                    self._send_negotiation(WONT, option)
                elif command == WILL:
                    self._send_negotiation(DONT, option)
                index += 3
                continue

            index += 2

        return bytes(output)

    @staticmethod
    def _skip_subnegotiation(data: bytes, index: int) -> int:
        while index + 1 < len(data):
            if data[index] == IAC and data[index + 1] == SE:
                return index + 2
            index += 1
        return len(data)

    def _send_negotiation(self, command: int, option: int) -> None:
        if not self.sock:
            return
        try:
            self.sock.sendall(bytes([IAC, command, option]))
        except OSError:
            return
