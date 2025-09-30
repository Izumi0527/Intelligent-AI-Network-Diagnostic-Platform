from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime

# 终端连接类型枚举
ConnectionType = Literal["ssh", "telnet"]

class TerminalCredentials(BaseModel):
    """终端连接凭证模型"""
    connection_type: ConnectionType = Field(..., description="连接类型: ssh 或 telnet")
    device_address: str = Field(..., description="设备地址(IP或域名)")
    port: int = Field(..., description="端口号")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    
    @validator('port')
    def validate_port(cls, v, values):
        connection_type = values.get('connection_type')
        if connection_type == 'ssh' and v not in [22, 2222]:
            if not v:  # 如果端口为空或0，设置为默认值
                return 22
        elif connection_type == 'telnet' and v not in [23, 2323]:
            if not v:  # 如果端口为空或0，设置为默认值
                return 23
        return v

class CommandRequest(BaseModel):
    """终端命令请求模型"""
    session_id: str = Field(..., description="会话ID")
    command: str = Field(..., description="要执行的命令")

class CommandResponse(BaseModel):
    """终端命令响应模型"""
    session_id: str = Field(..., description="会话ID")
    output: str = Field(..., description="命令执行输出")
    is_error: bool = Field(False, description="是否包含错误")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str = Field(..., description="会话ID")
    connection_type: ConnectionType
    device_address: str
    port: int
    username: str
    connected_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(True, description="会话是否活跃")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "connection_type": "ssh",
                "device_address": "192.168.1.1",
                "port": 22,
                "username": "admin",
                "connected_at": "2023-10-16T10:30:00",
                "last_activity": "2023-10-16T10:35:00",
                "is_active": True
            }
        }

class SessionList(BaseModel):
    """会话列表模型"""
    sessions: List[SessionInfo] = Field(default_factory=list)
    count: int = Field(..., description="会话总数")

class ConnectionResponse(BaseModel):
    """连接响应模型"""
    success: bool = Field(..., description="连接是否成功")
    session_id: Optional[str] = Field(None, description="会话ID（成功时）")
    message: str = Field(..., description="连接结果消息")
    device_info: Optional[str] = Field(None, description="设备信息（成功时）") 