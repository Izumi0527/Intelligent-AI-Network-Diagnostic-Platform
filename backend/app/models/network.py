from typing import Optional, Literal, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class Connection(BaseModel):
    """网络设备连接信息"""
    id: str = Field(..., description="连接ID")
    host: str = Field(..., description="主机地址")
    port: int = Field(..., description="端口号")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    connection_type: Literal["SSH", "Telnet"] = Field(..., description="连接类型")
    device_type: str = Field(..., description="设备类型（如cisco_ios, huawei, h3c等）")
    status: Literal["connected", "disconnected", "connecting", "failed"] = Field("disconnected", description="连接状态")
    last_connected: Optional[datetime] = Field(None, description="最后连接时间")
    last_error: Optional[str] = Field(None, description="最后错误信息")

class ConnectionRequest(BaseModel):
    """连接请求"""
    host: str = Field(..., description="主机地址")
    port: int = Field(..., description="端口号")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    connection_type: Literal["SSH", "Telnet"] = Field(..., description="连接类型")
    device_type: str = Field(..., description="设备类型")
    
    class Config:
        json_schema_extra = {
            "example": {
                "host": "192.168.1.1",
                "port": 22,
                "username": "admin",
                "password": "password",
                "connection_type": "SSH",
                "device_type": "cisco_ios"
            }
        }

class ConnectionResponse(BaseModel):
    """连接响应"""
    connection_id: str = Field(..., description="连接ID")
    status: Literal["connected", "failed"] = Field(..., description="连接状态")
    message: str = Field(..., description="状态消息")

class CommandRequest(BaseModel):
    """命令执行请求"""
    connection_id: str = Field(..., description="连接ID")
    command: str = Field(..., description="要执行的命令")
    
    class Config:
        json_schema_extra = {
            "example": {
                "connection_id": "conn-12345",
                "command": "show interface status"
            }
        }

class CommandResponse(BaseModel):
    """命令执行响应"""
    connection_id: str = Field(..., description="连接ID")
    command: str = Field(..., description="执行的命令")
    output: str = Field(..., description="命令输出")
    status: Literal["success", "failed"] = Field(..., description="执行状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="执行时间")

class DisconnectRequest(BaseModel):
    """断开连接请求"""
    connection_id: str = Field(..., description="连接ID")

class DisconnectResponse(BaseModel):
    """断开连接响应"""
    connection_id: str = Field(..., description="连接ID")
    status: Literal["success", "failed"] = Field(..., description="断开状态")
    message: str = Field(..., description="状态消息")

class ConnectionsListResponse(BaseModel):
    """连接列表响应"""
    connections: List[Connection] = Field(..., description="连接列表")

class NetworkEvent(BaseModel):
    """网络事件"""
    event_type: Literal["connection_change", "command_executed", "error"] = Field(..., description="事件类型")
    connection_id: Optional[str] = Field(None, description="连接ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="事件时间")
    data: Dict[str, Any] = Field(..., description="事件数据") 