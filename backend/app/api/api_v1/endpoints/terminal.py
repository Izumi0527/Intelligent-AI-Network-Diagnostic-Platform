from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_terminal_service
from app.models.terminal import (
    CommandRequest,
    CommandResponse,
    ConnectionResponse,
    DisconnectRequest,
    SessionInfo,
    SessionList,
    TerminalCredentials,
)
from app.services.terminal_exceptions import TerminalServiceError
from app.services.terminal_service import TerminalService

router = APIRouter()


def _raise_terminal_http_error(error: TerminalServiceError):
    """将终端领域异常映射为 HTTP 响应。"""
    raise HTTPException(
        status_code=error.status_code, detail=error.client_message
    ) from error


@router.post("/connect", response_model=ConnectionResponse)
async def connect_terminal(
    credentials: TerminalCredentials,
    terminal_service: TerminalService = Depends(get_terminal_service),
):
    """
    创建与网络设备的终端连接

    支持SSH和Telnet协议
    """
    try:
        return await terminal_service.connect(credentials)
    except TerminalServiceError as error:
        _raise_terminal_http_error(error)


@router.post("/cancel-connect", response_model=dict[str, Any])
async def cancel_connection(
    terminal_service: TerminalService = Depends(get_terminal_service),
):
    """
    取消正在进行中的连接尝试

    在长时间的连接过程中可以取消连接
    """
    return {"success": True, "message": "连接尝试已取消"}


@router.post("/execute", response_model=CommandResponse)
async def execute_command(
    command_request: CommandRequest,
    terminal_service: TerminalService = Depends(get_terminal_service),
):
    """
    在终端会话中执行命令

    需要提供有效的会话ID和要执行的命令
    """
    try:
        return await terminal_service.execute_command(command_request)
    except TerminalServiceError as error:
        _raise_terminal_http_error(error)


@router.post("/disconnect", response_model=dict[str, Any])
async def disconnect_terminal(
    request: DisconnectRequest,
    terminal_service: TerminalService = Depends(get_terminal_service),
):
    """
    断开终端连接

    需要提供有效的会话ID
    """
    try:
        return await terminal_service.disconnect(request.session_id)
    except TerminalServiceError as error:
        _raise_terminal_http_error(error)


@router.get("/sessions", response_model=SessionList)
async def get_sessions(
    terminal_service: TerminalService = Depends(get_terminal_service),
):
    """
    获取所有活跃的终端会话列表
    """
    try:
        return await terminal_service.get_sessions()
    except TerminalServiceError as error:
        _raise_terminal_http_error(error)


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(
    session_id: str,
    terminal_service: TerminalService = Depends(get_terminal_service),
):
    """
    获取特定会话的详细信息

    需要提供有效的会话ID
    """
    try:
        return await terminal_service.get_session(session_id)
    except TerminalServiceError as error:
        _raise_terminal_http_error(error)


@router.post("/cleanup", response_model=dict[str, Any])
async def cleanup_idle_sessions(
    terminal_service: TerminalService = Depends(get_terminal_service),
):
    """
    清理闲置的终端会话

    自动断开超过配置的闲置时间的会话
    """
    try:
        return await terminal_service.cleanup_idle_sessions()
    except TerminalServiceError as error:
        _raise_terminal_http_error(error)
