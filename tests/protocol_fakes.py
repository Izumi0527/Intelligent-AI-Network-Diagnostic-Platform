from types import SimpleNamespace


class ScriptedShell:
    """按脚本返回 SSH shell 数据，避免测试触碰真实设备。"""

    def __init__(self, *, recv_chunks, recv_ready_values=None):
        self._recv_chunks = list(recv_chunks)
        self._recv_ready_values = list(recv_ready_values or [])
        self.sent_data = []
        self.active = True
        self.closed = False

    def recv(self, _size):
        if self._recv_chunks:
            return self._recv_chunks.pop(0)
        return b""

    def recv_ready(self):
        if self._recv_ready_values:
            return self._recv_ready_values.pop(0)
        return bool(self._recv_chunks)

    def send(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.sent_data.append(data)
        return len(data)


class DisconnectingTelnetClient:
    """执行读取时模拟远端断开连接。"""

    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(data)

    def read_very_eager(self):
        raise ConnectionResetError("连接被远端断开")


class ScriptedAIManager:
    """按脚本输出 AI 流式事件或异常。"""

    def __init__(self, *, stream_events):
        self.stream_events = list(stream_events)
        self.stream_calls = 0

    async def chat_stream(self, _request):
        self.stream_calls += 1
        for item in self.stream_events:
            if isinstance(item, BaseException):
                raise item
            event_type, data = item
            yield SimpleNamespace(type=event_type, data=data)
