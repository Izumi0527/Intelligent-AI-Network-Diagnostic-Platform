import asyncio
import logging
import uuid
from typing import Dict, Optional, List, Any
from datetime import datetime

import netmiko
from netmiko import ConnectHandler

from app.models.network import (
    Connection, ConnectionRequest, ConnectionResponse,
    CommandRequest, CommandResponse, DisconnectRequest, 
    DisconnectResponse, ConnectionsListResponse
)

logger = logging.getLogger(__name__)

class NetworkService:
    """网络服务，处理SSH/Telnet连接和命令执行"""
    
    def __init__(self):
        """初始化网络服务"""
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()
    
    async def connect(self, request: ConnectionRequest) -> ConnectionResponse:
        """建立与网络设备的连接"""
        connection_id = f"conn-{uuid.uuid4().hex[:8]}"
        
        # 准备连接参数
        device_params = {
            'device_type': request.device_type,
            'host': request.host,
            'port': request.port,
            'username': request.username,
            'password': request.password,
        }
        
        if request.connection_type == "Telnet":
            device_params['device_type'] = f"{device_params['device_type']}_telnet"
        
        try:
            # 使用线程池执行阻塞的SSH/Telnet连接
            connection = await asyncio.to_thread(
                self._establish_connection, device_params
            )
            
            # 保存连接信息
            async with self.lock:
                self.connections[connection_id] = {
                    'connection': connection,
                    'info': Connection(
                        id=connection_id,
                        host=request.host,
                        port=request.port,
                        username=request.username,
                        password="******",  # 隐藏密码
                        connection_type=request.connection_type,
                        device_type=request.device_type,
                        status="connected",
                        last_connected=datetime.now()
                    )
                }
            
            return ConnectionResponse(
                connection_id=connection_id,
                status="connected",
                message=f"成功连接到 {request.host}"
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
                message=error_message
            )
    
    def _establish_connection(self, device_params: Dict[str, Any]) -> Any:
        """建立SSH/Telnet连接（同步方法，将在线程池中执行）"""
        return ConnectHandler(**device_params)
    
    async def execute_command(self, request: CommandRequest) -> CommandResponse:
        """在网络设备上执行命令"""
        connection_id = request.connection_id
        command = request.command
        
        # 检查连接是否存在
        if connection_id not in self.connections:
            return CommandResponse(
                connection_id=connection_id,
                command=command,
                output="错误: 连接不存在或已断开",
                status="failed",
                timestamp=datetime.now()
            )
        
        try:
            # 获取连接对象
            connection = self.connections[connection_id]['connection']
            
            # 使用线程池执行阻塞的命令
            output = await asyncio.to_thread(
                self._execute_command_sync, connection, command
            )
            
            return CommandResponse(
                connection_id=connection_id,
                command=command,
                output=output,
                status="success",
                timestamp=datetime.now()
            )
        
        except Exception as e:
            error_message = f"执行命令失败: {str(e)}"
            logger.error(error_message)
            
            # 更新连接状态
            if connection_id in self.connections:
                self.connections[connection_id]['info'].status = "failed"
                self.connections[connection_id]['info'].last_error = error_message
            
            return CommandResponse(
                connection_id=connection_id,
                command=command,
                output=error_message,
                status="failed",
                timestamp=datetime.now()
            )
    
    def _execute_command_sync(self, connection: Any, command: str) -> str:
        """执行命令（同步方法，将在线程池中执行）"""
        return connection.send_command(command)
    
    async def disconnect(self, request: DisconnectRequest) -> DisconnectResponse:
        """断开与网络设备的连接"""
        connection_id = request.connection_id
        
        # 检查连接是否存在
        if connection_id not in self.connections:
            return DisconnectResponse(
                connection_id=connection_id,
                status="failed",
                message="错误: 连接不存在或已断开"
            )
        
        try:
            # 获取连接对象
            connection = self.connections[connection_id]['connection']
            
            # 使用线程池执行阻塞的断开连接操作
            await asyncio.to_thread(self._disconnect_sync, connection)
            
            # 移除连接
            async with self.lock:
                del self.connections[connection_id]
            
            return DisconnectResponse(
                connection_id=connection_id,
                status="success",
                message="连接已成功断开"
            )
        
        except Exception as e:
            error_message = f"断开连接失败: {str(e)}"
            logger.error(error_message)
            
            # 强制移除连接
            async with self.lock:
                if connection_id in self.connections:
                    del self.connections[connection_id]
            
            return DisconnectResponse(
                connection_id=connection_id,
                status="failed",
                message=error_message
            )
    
    def _disconnect_sync(self, connection: Any) -> None:
        """断开连接（同步方法，将在线程池中执行）"""
        connection.disconnect()
    
    async def get_connections(self) -> ConnectionsListResponse:
        """获取所有当前连接"""
        connections_list = []
        
        async with self.lock:
            for conn_id, conn_data in self.connections.items():
                connections_list.append(conn_data['info'])
        
        return ConnectionsListResponse(connections=connections_list)
    
    async def check_connection_status(self, connection_id: str) -> Optional[Connection]:
        """检查连接状态"""
        if connection_id not in self.connections:
            return None
        
        return self.connections[connection_id]['info']