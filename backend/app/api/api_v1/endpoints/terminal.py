from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List

from app.services.terminal_service import TerminalService
from app.models.terminal import (
    TerminalCredentials, CommandRequest, CommandResponse,
    SessionInfo, SessionList, ConnectionResponse
)
from app.api.deps import get_terminal_service

router = APIRouter()

@router.post("/connect", response_model=ConnectionResponse)
async def connect_terminal(
    credentials: TerminalCredentials,
    terminal_service: TerminalService = Depends(get_terminal_service)
):
    """
    创建与网络设备的终端连接
    
    支持SSH和Telnet协议
    """
    return await terminal_service.connect(credentials)

@router.post("/cancel-connect", response_model=Dict[str, Any])
async def cancel_connection(
    terminal_service: TerminalService = Depends(get_terminal_service)
):
    """
    取消正在进行中的连接尝试
    
    在长时间的连接过程中可以取消连接
    """
    return {"success": True, "message": "连接尝试已取消"}

@router.post("/execute", response_model=CommandResponse)
async def execute_command(
    command_request: CommandRequest,
    terminal_service: TerminalService = Depends(get_terminal_service)
):
    """
    在终端会话中执行命令
    
    需要提供有效的会话ID和要执行的命令
    """
    return await terminal_service.execute_command(command_request)

@router.post("/disconnect", response_model=Dict[str, Any])
async def disconnect_terminal(
    session_id: str,
    terminal_service: TerminalService = Depends(get_terminal_service)
):
    """
    断开终端连接
    
    需要提供有效的会话ID
    """
    return await terminal_service.disconnect(session_id)

@router.get("/sessions", response_model=SessionList)
async def get_sessions(
    terminal_service: TerminalService = Depends(get_terminal_service)
):
    """
    获取所有活跃的终端会话列表
    """
    return await terminal_service.get_sessions()

@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    terminal_service: TerminalService = Depends(get_terminal_service)
):
    """
    获取特定会话的详细信息
    
    需要提供有效的会话ID
    """
    return await terminal_service.get_session(session_id)

@router.post("/cleanup", response_model=Dict[str, Any])
async def cleanup_idle_sessions(
    terminal_service: TerminalService = Depends(get_terminal_service)
):
    """
    清理闲置的终端会话
    
    自动断开超过配置的闲置时间的会话
    """
    return await terminal_service.cleanup_idle_sessions() 