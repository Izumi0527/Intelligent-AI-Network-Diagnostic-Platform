import logging
import time
from typing import Dict, List, Optional, Any

from fastapi import HTTPException, status
from pydantic import ValidationError

from app.core.terminal import TerminalManager
from app.models.terminal import (
    TerminalCredentials, CommandRequest, CommandResponse,
    SessionInfo, SessionList, ConnectionResponse
)
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class TerminalService:
    """终端服务层，处理API与核心终端功能之间的交互"""
    
    def __init__(self):
        """初始化终端服务"""
        self.terminal_manager = TerminalManager()
        self.max_sessions = settings.MAX_TERMINAL_SESSIONS
        self.idle_timeout = settings.SESSION_IDLE_TIMEOUT
    
    async def connect(self, credentials: TerminalCredentials) -> ConnectionResponse:
        """创建新的终端连接"""
        # 检查是否超过最大会话数
        sessions = await self.terminal_manager.get_all_sessions()
        if len(sessions) >= self.max_sessions:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"超过最大会话数限制 ({self.max_sessions})"
            )
        
        try:
            # 创建连接
            response = await self.terminal_manager.connect(
                connection_type=credentials.connection_type,
                device_address=credentials.device_address,
                port=credentials.port,
                username=credentials.username,
                password=credentials.password
            )
            
            # 如果连接失败，抛出异常
            if not response.success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=response.message
                )
                
            return response
            
        except ValidationError as e:
            logger.error(f"验证错误: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"验证错误: {str(e)}"
            )
            
        except Exception as e:
            logger.error(f"连接出错: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"连接出错: {str(e)}"
            )
    
    async def execute_command(self, command_request: CommandRequest) -> CommandResponse:
        """在终端会话中执行命令"""
        try:
            # 执行命令
            response = await self.terminal_manager.execute_command(
                session_id=command_request.session_id,
                command=command_request.command
            )
            
            # 如果有错误，记录日志
            if response.is_error:
                logger.warning(f"命令执行错误: {response.output}")
                
            return response
            
        except Exception as e:
            logger.error(f"执行命令出错: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"执行命令出错: {str(e)}"
            )
    
    async def disconnect(self, session_id: str) -> Dict[str, Any]:
        """断开终端连接"""
        try:
            # 断开连接
            success, message = await self.terminal_manager.disconnect(session_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=message
                )
                
            return {"success": True, "message": message}
            
        except HTTPException:
            raise
            
        except Exception as e:
            logger.error(f"断开连接出错: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"断开连接出错: {str(e)}"
            )
    
    async def get_sessions(self) -> SessionList:
        """获取所有活跃会话"""
        try:
            sessions = await self.terminal_manager.get_all_sessions()
            return SessionList(sessions=sessions, count=len(sessions))
            
        except Exception as e:
            logger.error(f"获取会话列表出错: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取会话列表出错: {str(e)}"
            )
    
    async def get_session(self, session_id: str) -> SessionInfo:
        """获取特定会话的信息"""
        try:
            session = await self.terminal_manager.get_session(session_id)
            
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"会话不存在: {session_id}"
                )
                
            return session
            
        except HTTPException:
            raise
            
        except Exception as e:
            logger.error(f"获取会话信息出错: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取会话信息出错: {str(e)}"
            )
    
    async def cleanup_idle_sessions(self) -> Dict[str, Any]:
        """清理闲置的会话"""
        try:
            cleaned_count = await self.terminal_manager.cleanup_idle_sessions(
                idle_timeout=self.idle_timeout
            )
            
            return {
                "success": True,
                "message": f"已清理 {cleaned_count} 个闲置会话",
                "cleaned_count": cleaned_count
            }
            
        except Exception as e:
            logger.error(f"清理闲置会话出错: {str(e)}")
            return {
                "success": False,
                "message": f"清理闲置会话出错: {str(e)}",
                "cleaned_count": 0
            } 