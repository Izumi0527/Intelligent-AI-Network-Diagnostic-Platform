from fastapi import APIRouter, HTTPException, status

from app.models.network import (
    ConnectionRequest, ConnectionResponse, CommandRequest, CommandResponse,
    DisconnectRequest, DisconnectResponse,
    ConnectionsListResponse, Connection
)

router = APIRouter()


NETWORK_DEPRECATED_DETAIL = {
    "message": "/network 连接接口已废弃，请迁移到 /terminal。",
    "replacement": "/api/v1/terminal",
}


def raise_network_gone() -> None:
    """旧 /network 写接口不再承载连接能力。"""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=NETWORK_DEPRECATED_DETAIL,
    )


@router.post("/connect", response_model=ConnectionResponse)
async def connect(request: ConnectionRequest):
    """建立SSH/Telnet连接"""
    raise_network_gone()

@router.post("/command", response_model=CommandResponse)
async def execute_command(request: CommandRequest):
    """执行网络设备命令"""
    raise_network_gone()

@router.post("/disconnect", response_model=DisconnectResponse)
async def disconnect(request: DisconnectRequest):
    """断开SSH/Telnet连接"""
    raise_network_gone()

@router.get("/connections", response_model=ConnectionsListResponse)
async def get_connections():
    """获取所有当前连接"""
    return ConnectionsListResponse(connections=[])

@router.get("/connections/{connection_id}", response_model=Connection)
async def get_connection_status(connection_id: str):
    """获取指定连接的状态"""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"连接不存在: {connection_id}，请使用 /terminal/sessions 查询终端会话",
    )
