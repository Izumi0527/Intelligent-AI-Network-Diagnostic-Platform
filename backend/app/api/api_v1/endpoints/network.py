from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.models.network import (
    ConnectionRequest, ConnectionResponse, CommandRequest, 
    CommandResponse, DisconnectRequest, DisconnectResponse,
    ConnectionsListResponse, Connection
)
from app.services.network_service import NetworkService
from app.api.deps import get_network_service

router = APIRouter()

@router.post("/connect", response_model=ConnectionResponse)
async def connect(
    request: ConnectionRequest,
    network_service: NetworkService = Depends(get_network_service)
):
    """建立SSH/Telnet连接"""
    response = await network_service.connect(request)
    if response.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response.message
        )
    return response

@router.post("/command", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    network_service: NetworkService = Depends(get_network_service)
):
    """执行网络设备命令"""
    response = await network_service.execute_command(request)
    if response.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response.output
        )
    return response

@router.post("/disconnect", response_model=DisconnectResponse)
async def disconnect(
    request: DisconnectRequest,
    network_service: NetworkService = Depends(get_network_service)
):
    """断开SSH/Telnet连接"""
    response = await network_service.disconnect(request)
    if response.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response.message
        )
    return response

@router.get("/connections", response_model=ConnectionsListResponse)
async def get_connections(
    network_service: NetworkService = Depends(get_network_service)
):
    """获取所有当前连接"""
    return await network_service.get_connections()

@router.get("/connections/{connection_id}", response_model=Connection)
async def get_connection_status(
    connection_id: str,
    network_service: NetworkService = Depends(get_network_service)
):
    """获取指定连接的状态"""
    connection = await network_service.check_connection_status(connection_id)
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"连接不存在: {connection_id}"
        )
    return connection 