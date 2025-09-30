"""
网络连接基础抽象类
提供统一的网络设备连接接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import uuid


class DeviceType(Enum):
    """设备类型枚举"""
    UNKNOWN = "unknown"
    HUAWEI = "huawei"
    CISCO = "cisco"
    JUNIPER = "juniper" 
    H3C = "h3c"


class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class NetworkConnection(ABC):
    """网络连接基类"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.session_id = str(uuid.uuid4())
        self.status = ConnectionStatus.DISCONNECTED
        self.device_type = DeviceType.UNKNOWN
        self.client = None
        self.connection_time = None
        self.last_activity_time = None
    
    @abstractmethod
    async def connect(self, timeout: int = 30) -> Tuple[bool, str]:
        """建立连接"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> Tuple[bool, str]:
        """断开连接"""
        pass
    
    @abstractmethod
    async def execute_command(self, command: str) -> Tuple[bool, str]:
        """执行命令"""
        pass
    
    @abstractmethod
    def is_alive(self) -> bool:
        """检查连接是否活跃"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            "session_id": self.session_id,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "status": self.status.value,
            "device_type": self.device_type.value,
            "connection_time": self.connection_time,
            "last_activity_time": self.last_activity_time
        }