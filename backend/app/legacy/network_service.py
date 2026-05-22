import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from netmiko import ConnectHandler

from app.models.network import (
    CommandRequest,
    CommandResponse,
    Connection,
    ConnectionRequest,
    ConnectionResponse,
    ConnectionsListResponse,
    DisconnectRequest,
    DisconnectResponse,
)

logger = logging.getLogger(__name__)


class NetworkService:
    """历史网络连接服务，仅供迁移参考，不再由运行时依赖层初始化。"""

    def __init__(self):
        self.connections: dict[str, dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def connect(self, request: ConnectionRequest) -> ConnectionResponse:
        """建立与网络设备的连接。"""
        connection_id = f"conn-{uuid.uuid4().hex[:8]}"
        device_params = {
            "device_type": request.device_type,
            "host": request.host,
            "port": request.port,
            "username": request.username,
            "password": request.password,
        }

        if request.connection_type == "Telnet":
            device_params["device_type"] = f"{device_params['device_type']}_telnet"

        try:
            connection = await asyncio.to_thread(
                self._establish_connection,
                device_params,
            )

            async with self.lock:
                self.connections[connection_id] = {
                    "connection": connection,
                    "info": Connection(
                        id=connection_id,
                        host=request.host,
                        port=request.port,
                        username=request.username,
                        password="******",
                        connection_type=request.connection_type,
                        device_type=request.device_type,
                        status="connected",
                        last_connected=datetime.now(),
                    ),
                }

            return ConnectionResponse(
                connection_id=connection_id,
                status="connected",
                message=f"成功连接到 {request.host}",
            )
        except Exception as e:
            error_type = type(e).__name__
            if error_type == "NetmikoTimeoutException":
                error_message = f"连接超时: {request.host}:{request.port}"
            elif error_type == "NetmikoAuthenticationException":
                error_message = f"认证失败: {request.host} (用户名: {request.username})"
            else:
                error_message = f"连接失败: {str(e)}"

            logger.error(error_message)
            return ConnectionResponse(
                connection_id=connection_id,
                status="failed",
                message=error_message,
            )

    def _establish_connection(self, device_params: dict[str, Any]) -> Any:
        """建立 SSH/Telnet 连接。"""
        return ConnectHandler(**device_params)

    async def execute_command(self, request: CommandRequest) -> CommandResponse:
        """在网络设备上执行命令。"""
        connection_id = request.connection_id
        command = request.command
        if connection_id not in self.connections:
            return CommandResponse(
                connection_id=connection_id,
                command=command,
                output="错误: 连接不存在或已断开",
                status="failed",
                timestamp=datetime.now(),
            )

        try:
            connection = self.connections[connection_id]["connection"]
            output = await asyncio.to_thread(
                self._execute_command_sync,
                connection,
                command,
            )

            return CommandResponse(
                connection_id=connection_id,
                command=command,
                output=output,
                status="success",
                timestamp=datetime.now(),
            )
        except Exception as e:
            error_message = f"执行命令失败: {str(e)}"
            logger.error(error_message)
            if connection_id in self.connections:
                self.connections[connection_id]["info"].status = "failed"
                self.connections[connection_id]["info"].last_error = error_message

            return CommandResponse(
                connection_id=connection_id,
                command=command,
                output=error_message,
                status="failed",
                timestamp=datetime.now(),
            )

    def _execute_command_sync(self, connection: Any, command: str) -> str:
        """同步执行设备命令。"""
        return connection.send_command(command)

    async def disconnect(self, request: DisconnectRequest) -> DisconnectResponse:
        """断开与网络设备的连接。"""
        connection_id = request.connection_id
        if connection_id not in self.connections:
            return DisconnectResponse(
                connection_id=connection_id,
                status="failed",
                message="错误: 连接不存在或已断开",
            )

        try:
            connection = self.connections[connection_id]["connection"]
            await asyncio.to_thread(self._disconnect_sync, connection)
            async with self.lock:
                del self.connections[connection_id]

            return DisconnectResponse(
                connection_id=connection_id,
                status="success",
                message="连接已成功断开",
            )
        except Exception as e:
            error_message = f"断开连接失败: {str(e)}"
            logger.error(error_message)

            async with self.lock:
                self.connections.pop(connection_id, None)

            return DisconnectResponse(
                connection_id=connection_id,
                status="failed",
                message=error_message,
            )

    def _disconnect_sync(self, connection: Any) -> None:
        """同步断开连接。"""
        connection.disconnect()

    async def get_connections(self) -> ConnectionsListResponse:
        """获取所有当前连接。"""
        async with self.lock:
            return ConnectionsListResponse(
                connections=[item["info"] for item in self.connections.values()],
            )

    async def check_connection_status(self, connection_id: str) -> Connection | None:
        """检查连接状态。"""
        if connection_id not in self.connections:
            return None

        return self.connections[connection_id]["info"]
